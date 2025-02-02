import os
import base64
from together import Together
from dotenv import load_dotenv

# Load API key from .env file
load_dotenv()
TOGETHER_API_KEY = os.getenv("TOGETHER_API_KEY")

# Initialize Together AI client
client = Together(api_key=TOGETHER_API_KEY)

def choose_image_ratio():
    """
    Presents 3 ratio options to the user and returns the width and height.
    Option 1: 16:9  (width=1024, height=576)
    Option 2: 4:3   (width=1024, height=768)
    Option 3: 1:1   (width=1024, height=1024)
    """
    print("\nSelect an image ratio:")
    print("1. 16:9  (1024x576)")
    print("2. 4:3   (1024x768)")
    print("3. 1:1   (1024x1024)")
    choice = input("Enter option number (1/2/3): ").strip()
    
    if choice == "1":
        return 1024, 576
    elif choice == "2":
        return 1024, 768
    elif choice == "3":
        return 1024, 1024
    else:
        print("Invalid choice. Defaulting to 4:3 ratio (1024x768).")
        return 1024, 768

def generate_image(prompt, width, height):
    """
    Generate an image using Together AI's image generation API.
    Uses steps=4 (as recommended) and seed=0.
    Returns the base64 image data.
    """
    try:
        response = client.images.generate(
            prompt=prompt,
            model="black-forest-labs/FLUX.1-schnell-Free",
            width=width,
            height=height,
            steps=4,          # Fixed steps as recommended.
            n=1,
            seed=0,           # Using 0 for deterministic results; you can try -1 for randomness.
            response_format="b64_json"
        )
        if response.data and len(response.data) > 0:
            return response.data[0].b64_json
        else:
            print("No image data received.")
            return None
    except Exception as e:
        print("Error during image generation:", e)
        return None

def save_image(b64_image_data, filename="generated_image.png"):
    """
    Decodes the base64 image data and saves it as a PNG file.
    """
    try:
        image_bytes = base64.b64decode(b64_image_data)
        with open(filename, "wb") as img_file:
            img_file.write(image_bytes)
        print(f"✅ Image saved as: {filename}")
    except Exception as e:
        print("Error saving image:", e)

def main():
    user_prompt = input("\nEnter a description for the image you want: ").strip()
    # Directly use the user's prompt for image generation
    print("\nUsing prompt:", user_prompt)
    
    width, height = choose_image_ratio()
    print(f"\n⏳ Generating image at {width}x{height} resolution...")
    
    b64_data = generate_image(user_prompt, width, height)
    if b64_data:
        save_image(b64_data)
    else:
        print("❌ Failed to generate image.")

if __name__ == "__main__":
    main()
