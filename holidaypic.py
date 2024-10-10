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

# Initialize colorama
init()

print(Fore.CYAN + "🚀 Starting the process..." + Style.RESET_ALL)

# Load environment variables
load_dotenv('.env.local')

# Modify the ArgumentParser section
parser = argparse.ArgumentParser(description="Generate and optionally email a daily user picture.")
parser.add_argument("--no-email", action="store_true", help="Skip sending email")
parser.add_argument("--control-image", type=str, help="Path or URL to custom control image")
args = parser.parse_args()

# Step 1: Generate prompt using @Ell
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

@ell.simple(model="gpt-4o-mini-2024-07-18", max_tokens=128)
def generate_foreground_object():
    return f"""
        Based on the holiday "{holiday_title}", suggest a single object or emoji that would best represent this holiday as a large, bold foreground element in an image. Output only the object or emoji name, nothing else.
    """

print(Fore.YELLOW + "🎨 Generating holiday prompt..." + Style.RESET_ALL)
holiday_json = generate_holiday_prompt()
holiday_data = json.loads(holiday_json)
holiday_title = holiday_data['title']
holiday_emoji = holiday_data['emoji']
holiday_description = holiday_data['description']
holiday_prompt = holiday_data['prompt']

print(Fore.YELLOW + "🖼️ Generating foreground object..." + Style.RESET_ALL)
holiday_object = generate_foreground_object()
full_prompt = f"Large bold {holiday_object} at the foreground. High contrast. " + holiday_prompt

print(Fore.GREEN + f"🎉 Generated holiday: {holiday_emoji} {holiday_title}" + Style.RESET_ALL)
print(Fore.GREEN + f"📅 Description: {holiday_description}" + Style.RESET_ALL)
print(Fore.GREEN + f"🖼️ Foreground object: {holiday_object}" + Style.RESET_ALL)
print(Fore.GREEN + f"📝 Generated prompt: {full_prompt}" + Style.RESET_ALL)

# Step 2: Generate image using Replicate
print(Fore.YELLOW + "🖼️ Generating image using Replicate..." + Style.RESET_ALL)

# Generate depth map
depth_output = replicate.run(
    "chenxwh/depth-anything-v2:b239ea33cff32bb7abb5db39ffe9a09c14cbc2894331d1ef66fe096eed88ebd4",
    input={
        "image": args.control_image or os.environ.get('CONTROL_IMAGE', 'https://replicate.delivery/pbxt/Ll54VZSXgicY76IolH5uDcTgUHKO8Aj3nyNhApW0EyeBEyEj/Sliday%20Logo2.jpg'),
        "model_size": "Large"
    }
)

# Extract the grey depth map URL
grey_depth_url = depth_output['grey_depth']

# Download the grey depth map
response = requests.get(grey_depth_url)
if response.status_code != 200:
    print(Fore.RED + f"Failed to download depth map. Status code: {response.status_code}" + Style.RESET_ALL)
    sys.exit(1)

depth_map_data = response.content

# Encode the image data as base64
depth_map_base64 = base64.b64encode(depth_map_data).decode('utf-8')

# Use the base64-encoded depth map as control_image
output = replicate.run(
    "xlabs-ai/flux-dev-controlnet:f2c31c31d81278a91b2447a304dae654c64a5d5a70340fba811bb1cbd41019a2",
    input={
        "steps": 28,
        "prompt": full_prompt,
        "lora_url": "",
        "control_type": "depth",
        "control_image": f"data:image/png;base64,{depth_map_base64}",
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
image_url = output[0]
print(Fore.GREEN + f"🖼️ Image generated. URL: {image_url}" + Style.RESET_ALL)

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