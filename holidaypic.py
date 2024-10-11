import ell
import replicate
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
import requests
from colorama import Fore, Style, init
import datetime
import json
import os
from dotenv import load_dotenv
import re
from datetime import date
import argparse
import sys
import base64
import time
import httpx

# Initialize colorama
init()

print(Fore.CYAN + "🚀 Starting the process..." + Style.RESET_ALL)

# Load environment variables
load_dotenv('.env.local')

# Modify the ArgumentParser section
parser = argparse.ArgumentParser(description="Generate and optionally email a daily user picture.")
parser.add_argument("--no-email", action="store_true", help="Skip sending email")
parser.add_argument("--control-image", type=str, help="Path or URL to custom control image")
parser.add_argument("--no-depth-processing", action="store_true", help="Skip depth map processing (use if control image is already a B&W depth map)")
args = parser.parse_args()

# Move these functions to the top of the file
@ell.simple(model="gpt-4o-mini-2024-07-18", max_tokens=100)
def analyze_control_image(image_url):
    """Analyze the control image and return a detailed description of the main object for Flux Replicate control."""
    return f"""
    Analyze the image at {image_url}. Provide a 3-word definition of the main object.
    Simply answer the question: What is it?

    Example: "Large letter 'S'"

    Keep the description under 4 words.
    No intro, no comments, no explanation. Output only the description, nothing else.
    """

@ell.simple(model="gpt-4o-mini-2024-07-18", max_tokens=128)
def stylize_object_for_holiday(object_description, holiday_title):
    """Stylize the main object description according to the holiday theme."""
    return f"""
    Given the main object description "{object_description}" and the holiday "{holiday_title}", 
    create a stylized version of this object that fits the holiday theme. 
    Keep it concise and suitable for a Stable Diffusion prompt. 
    Output only the stylized description, nothing else.
    """

# Add this function for retrying API calls
def retry_api_call(func, max_retries=3, delay=5):
    for attempt in range(max_retries):
        try:
            return func()
        except (httpx.ReadTimeout, httpx.ConnectTimeout) as e:
            if attempt == max_retries - 1:
                raise
            print(Fore.YELLOW + f"API call failed. Retrying in {delay} seconds..." + Style.RESET_ALL)
            time.sleep(delay)

# Step 1: Analyze control image
print(Fore.YELLOW + "🖼️ Analyzing control image..." + Style.RESET_ALL)
control_image = args.control_image or os.environ.get('CONTROL_IMAGE', 'https://replicate.delivery/pbxt/Ll54VZSXgicY76IolH5uDcTgUHKO8Aj3nyNhApW0EyeBEyEj/Sliday%20Logo2.jpg')
main_object_description = analyze_control_image(control_image)
print(Fore.GREEN + f"🖼️ Main object description: {main_object_description}" + Style.RESET_ALL)

# Step 2: Generate depth map if needed
if not args.no_depth_processing:
    print(Fore.YELLOW + "🗺️ Generating depth map..." + Style.RESET_ALL)
    try:
        depth_output = retry_api_call(lambda: replicate.run(
            "chenxwh/depth-anything-v2:b239ea33cff32bb7abb5db39ffe9a09c14cbc2894331d1ef66fe096eed88ebd4",
            input={
                "image": control_image,
                "model_size": "Large"
            }
        ))
        grey_depth_url = depth_output['grey_depth']
        response = requests.get(grey_depth_url)
        if response.status_code != 200:
            raise Exception(f"Failed to download depth map. Status code: {response.status_code}")
        depth_map_data = response.content
        depth_map_base64 = base64.b64encode(depth_map_data).decode('utf-8')
        control_image = f"data:image/png;base64,{depth_map_base64}"
        print(Fore.GREEN + "✅ Depth map generated successfully." + Style.RESET_ALL)
    except Exception as e:
        print(Fore.YELLOW + f"Failed to generate depth map: {str(e)}. Using original control image." + Style.RESET_ALL)
else:
    print(Fore.YELLOW + "🗺️ Using provided image as depth map..." + Style.RESET_ALL)

# Step 3: Generate holiday prompt
print(Fore.YELLOW + "🎨 Generating holiday prompt..." + Style.RESET_ALL)
@ell.simple(model="claude-3-5-sonnet-20240620", max_tokens=256)
def generate_holiday_prompt():
    today = datetime.date.today()
    f"""You're a holiday master. """
    return f"""
        Look up in your worldwide holiday register, think of top 10 worldwide holidays for {today.strftime('%B %d, %Y')}, pick the most interesting and unorthodox holiday and create a Stable Diffusion prompt (max 500 characters) for the image that represents this holiday the best. No comments, no intro, only the prompt.
        Use JSON format to output the result:
        {{
            "type": "object",
            "properties": {{
                "title": {{
                    "type": "string",
                    "description": "The title of the holiday"
                }},
                "emoji": {{
                    "type": "string",
                    "description": "A single emoji that best represents the holiday"
                }},
                "description": {{
                    "type": "string",
                    "description": "A short description (max 100 characters) that mentions the date and explains the holiday in a simple way"
                }},
                "prompt": {{
                    "type": "string",
                    "description": "The Stable Diffusion prompt for the image"
                }}
            }},
            "required": ["title", "emoji", "description", "prompt"]
        }}
        No \`\`\`json\`\`\` code block, no comments, no intro, only the JSON.
    """

holiday_json = generate_holiday_prompt()
holiday_data = json.loads(holiday_json)
holiday_title = holiday_data['title']
holiday_emoji = holiday_data['emoji']
holiday_description = holiday_data['description']
holiday_prompt = holiday_data['prompt']

# Step 4: Generate foreground object
print(Fore.YELLOW + "🖼️ Generating foreground object..." + Style.RESET_ALL)
@ell.simple(model="gpt-4o-mini-2024-07-18", max_tokens=128)
def generate_foreground_object():
    return f"""
        Based on the holiday "{holiday_title}", suggest a single object or emoji that would best represent this holiday as a large, bold foreground element in an image. Output only the object or emoji name, nothing else.
    """

holiday_object = generate_foreground_object()

# Step 5: Stylize object for holiday
print(Fore.YELLOW + "🎨 Stylizing object for holiday..." + Style.RESET_ALL)
stylized_object = stylize_object_for_holiday(main_object_description, holiday_title)
print(Fore.GREEN + f"🎨 Stylized object: {stylized_object}" + Style.RESET_ALL)

# Step 6: Generate full prompt
full_prompt = f"Large bold {holiday_object} ({stylized_object}) at the foreground. High contrast. " + holiday_prompt

print(Fore.GREEN + f"🎉 Generated holiday: {holiday_emoji} {holiday_title}" + Style.RESET_ALL)
print(Fore.GREEN + f"📅 Description: {holiday_description}" + Style.RESET_ALL)
print(Fore.GREEN + f"🖼️ Foreground object: {holiday_object}" + Style.RESET_ALL)
print(Fore.GREEN + f"📝 Generated prompt: {full_prompt}" + Style.RESET_ALL)

# Step 7: Generate image using Replicate
print(Fore.YELLOW + "🖼️ Generating image using Replicate..." + Style.RESET_ALL)

# Use the control_image (either depth map or original image) for image generation
def generate_image():
    return replicate.run(
        "xlabs-ai/flux-dev-controlnet:f2c31c31d81278a91b2447a304dae654c64a5d5a70340fba811bb1cbd41019a2",
        input={
            "steps": 28,
            "prompt": full_prompt,
            "lora_url": "",
            "control_type": "depth",
            "control_image": control_image,
            "lora_strength": 1,
            "output_format": "jpg",
            "guidance_scale": 3.52,
            "output_quality": 80,
            "negative_prompt": "low quality, ugly, distorted, artefacts, low contrast",
            "control_strength": 0.68,
            "depth_preprocessor": "DepthAnything",
            "soft_edge_preprocessor": "HED",
            "image_to_image_strength": 0,
            "return_preprocessed_image": False
        }
    )

try:
    output = retry_api_call(generate_image)
    image_url = output[0]
    print(Fore.GREEN + f"🖼️ Image generated. URL: {image_url}" + Style.RESET_ALL)
except Exception as e:
    print(Fore.RED + f"Failed to generate image: {str(e)}. Trying a simpler model..." + Style.RESET_ALL)
    try:
        output = retry_api_call(lambda: replicate.run(
            "stability-ai/stable-diffusion:ac732df83cea7fff18b8472768c88ad041fa750ff7682a21affe81863cbe77e4",
            input={"prompt": full_prompt}
        ))
        image_url = output[0]
        print(Fore.GREEN + f"🖼️ Image generated with fallback model. URL: {image_url}" + Style.RESET_ALL)
    except Exception as e:
        print(Fore.RED + f"Failed to generate image with fallback model: {str(e)}. Exiting." + Style.RESET_ALL)
        sys.exit(1)

# Download and save the image locally
print(Fore.YELLOW + "💾 Saving image locally..." + Style.RESET_ALL)

# Create a valid filename from the holiday title
def create_valid_filename(title):
    # Remove any characters that are not alphanumeric, space, or underscore
    clean_title = re.sub(r'[^\w\s-]', '', title)
    # Replace spaces with underscores
    return clean_title.replace(' ', '_')

# Get current date
current_date = date.today().strftime("%Y-%m-%d")

# Create filename
filename = f"{current_date}_{create_valid_filename(holiday_title)}.jpg"

# Ensure the filename is not too long
if len(filename) > 255:  # Maximum filename length on most systems
    filename = filename[:251] + ".jpg"  # Truncate and keep the extension

# Download and save the image
response = requests.get(image_url)
if response.status_code == 200:
    with open(filename, 'wb') as file:
        file.write(response.content)
    print(Fore.GREEN + f"✅ Image saved as: {filename}" + Style.RESET_ALL)
else:
    print(Fore.RED + f"❌ Failed to download image. Status code: {response.status_code}" + Style.RESET_ALL)

# Update image_data for email attachment
image_data = response.content

# Modify the email sending part
if not args.no_email:
    print(Fore.YELLOW + "📧 Sending email..." + Style.RESET_ALL)
    # Create the email
    message = MIMEMultipart()
    message["From"] = os.getenv('SENDER_EMAIL')
    message["To"] = os.getenv('RECEIVER_EMAIL')
    message["Subject"] = f"{holiday_emoji} {holiday_title}"

    # Create the HTML content with embedded image
    html_content = f"""
    <html>
      <body>
        <h2 style="font-family: sans-serif; font-size: 18px; font-weight: bold; color: #333;">{holiday_description}</h2>
        <img src="cid:holiday_image" alt="Holiday Image" style="max-width: 100%;">
      </body>
    </html>
    """

    # Create the HTML part
    html_part = MIMEText(html_content, 'html')
    message.attach(html_part)

    # Embed the image
    image = MIMEImage(image_data)
    image.add_header('Content-ID', '<holiday_image>')
    image.add_header('Content-Disposition', 'inline', filename=filename)
    message.attach(image)

    # Send the email
    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(os.getenv('SENDER_EMAIL'), os.getenv('SENDER_PASSWORD'))
            server.send_message(message)
        print(Fore.GREEN + "📨 Email sent successfully!" + Style.RESET_ALL)
    except Exception as e:
        print(Fore.RED + f"❌ Error sending email: {str(e)}" + Style.RESET_ALL)
else:
    print(Fore.YELLOW + "📧 Skipping email send." + Style.RESET_ALL)

print(Fore.CYAN + "🎊 Process completed!" + Style.RESET_ALL)