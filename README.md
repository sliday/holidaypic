# Holiday Pic: Daily Stylized Avatar/Brand Image Generator

This Python script generates a unique daily image based on a holiday theme and sends it via email. It uses AI-powered image generation and integrates with various services to create a personalized experience.

![Prediction webp from xlabs-ai (1) 2](https://github.com/user-attachments/assets/b1e7314c-c287-44ea-a9c1-56e34f8becc2)

## Features

- Generates a daily holiday prompt using AI
- Creates a custom image using Replicate's AI image generation
- Sends the generated image via email
- Uses environment variables for configuration
- Provides interactive prompts for missing configuration

## Prerequisites

- Python 3.6+
- A Gmail account (for sending emails)
- Replicate API access

## Installation

1. Clone this repository or download the `holidaypic.py` script.
2. Create a new virtual environment using built-in `venv` module:

```bash
python3 -m venv .venv
```

3. Activate the virtual environment:

```bash
source .venv/bin/activate
```

4. Install the required Python packages:

```bash
pip install -r requirements.txt
```

5. Create a `.env.local` file in the same directory as the script with the following variables:

```bash
SENDER_EMAIL=your_gmail@gmail.com
SENDER_PASSWORD=your_gmail_password
RECEIVER_EMAIL=recipient@example.com
CONTROL_IMAGE=https://example.com/path/to/control/image.jpg
```

6. (Optional) To deactivate the virtual environment, run:

```bash
deactivate
```

## Usage

Run the script using Python:

```bash
python3 holidaypic.py [options]
```
If any required environment variables are missing, the script will prompt you to enter them interactively.

## Command-line Arguments

The script supports several command-line arguments to customize its behavior:

- `--no-email`: Skip sending the generated image via email.
- `--control-image PATH`: Specify a custom control image to use instead of the default.
- `--no-depth-processing`: Skip depth map processing for the control image.

### Examples

1. Generate an image and send it via email (default behavior):
   ```bash
   python3 holidaypic.py
   ```

2. Generate an image without sending an email:
   ```bash
   python3 holidaypic.py --no-email
   ```

3. Use a custom control image:
   ```bash
   python3 holidaypic.py --control-image path/to/your/image.jpg
   ```

4. Use a custom control image that's already a black and white depth map:
   ```bash
   python3 holidaypic.py --control-image path/to/depth_map.jpg --no-depth-processing
   ```

### Argument Details

- `--no-email`: Use this flag when you want to generate the image but don't want to send it via email. This is useful for testing or when you want to manually handle the generated image.

- `--control-image PATH`: This argument allows you to specify a custom image to use as the control for the AI image generation. The control image influences the structure and composition of the generated image. If not provided, the script uses a default control image.

- `--no-depth-processing`: By default, the script processes the control image to create a depth map. Use this flag if your control image is already a black and white depth map and you want to skip this processing step. This can be useful when you have pre-processed images or want more direct control over the depth information used in image generation.

## How It Works

1. The script generates a holiday prompt using AI.
2. It uses the generated prompt to create a custom image with Replicate's AI image generation service.
3. The generated image is then sent via email to the specified recipient.

## Configuration

- `SENDER_EMAIL`: The Gmail address used to send the email
- `SENDER_PASSWORD`: An App Password for your Gmail account (see script output for instructions on creating one)
- `RECEIVER_EMAIL`: The email address that will receive the generated image
- `CONTROL_IMAGE`: URL of the control image used in the AI image generation process
- `REPLICATE_API`: Your Replicate API key for accessing the AI image generation service

## Note

> [!WARNING]  
> Make sure to keep your `.env.local` file secure and never commit it to version control systems.

## Setting Up Daily Execution

1. Create `run_holidaypic.sh`:

   ```bash
   #!/bin/bash
   cd /path/to/script/directory
   /path/to/python3 holidaypic.py
   ```

   Adjust paths as needed. Add `--no-email` at the end to skip sending emails.

2. Make it executable:

   ```bash
   chmod +x run_holidaypic.sh
   ```

3. Add to crontab:

   ```
   crontab -e
   ```

   Add this line to run daily at 9 AM:

   ```
   0 9 * * * /path/to/run_holidaypic.sh
   ```

4. Save and exit the crontab editor.

The script will now run automatically every day at 9 AM, generating an image and emailing it by default.
