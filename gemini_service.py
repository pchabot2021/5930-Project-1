import os
import json
import tempfile
import google.generativeai as genai
import logging

logger = logging.getLogger(__name__)

def process_image(image_bytes, filename):
    """
    Process an image with Gemini API to get title and description.
    
    Args:
        image_bytes: Binary content of the image
        filename: Original filename
        
    Returns:
        dict: JSON with title and description
    """
    try:
        # Initialize Gemini API
        api_key = os.environ.get('GEMINI_API')
        if not api_key:
            logger.error("GEMINI_API environment variable not set")
            raise ValueError("GEMINI_API key is required")
        
        genai.configure(api_key=api_key)
        
        # Configure generation parameters
        generation_config = {
            "temperature": 1,
            "top_p": 0.95,
            "top_k": 64,
            "max_output_tokens": 8192,
            "response_mime_type": "application/json",
        }
        
        # Initialize model
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            # generation_config=generation_config,
        )
        
        # Create a temporary file for the image
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(filename)[1]) as temp_file:
            temp_file.write(image_bytes)
            temp_path = temp_file.name
        
        try:
            # Prepare prompt for Gemini
            prompt = """
            Analyze this image and provide a detailed description.
            Return your response in the following JSON format:
            {
                "title": "A concise, catchy title for this image",
                "description": "A detailed description of what's in the image"
            }
            Just return the JSON with no additional text.
            """
            
            # Upload file to Gemini with mime type
            mime_type = f"image/{os.path.splitext(filename)[1][1:]}" if os.path.splitext(filename)[1][1:] else "image/jpeg"
            file = genai.upload_file(temp_path, mime_type=mime_type)
            logger.info(f"Uploaded file to Gemini for processing with mime_type: {mime_type}")
            
            # Generate content
            response = model.generate_content([file, prompt])
            logger.info("Received response from Gemini API")
            
            # Parse response
            response_text = response.text
            
            # Handle the case where the response might have markdown code blocks
            if "```json" in response_text:
                json_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                json_text = response_text.split("```")[1].strip()
            else:
                json_text = response_text.strip()
            
            try:
                result = json.loads(json_text)
                
                # Ensure the result has the required fields
                if "title" not in result or "description" not in result:
                    logger.warning("Gemini response missing required fields")
                    result = {
                        "title": f"Image: {filename}",
                        "description": "Analyzed image content."
                    }
            except json.JSONDecodeError:
                logger.warning(f"Could not parse Gemini response as JSON: {response_text[:100]}...")
                result = {
                    "title": f"Image: {filename}",
                    "description": response_text[:500]  # Use part of the response as description
                }
            
            return result
        finally:
            # Clean up the temp file
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    except Exception as e:
        logger.error(f"Error processing image with Gemini: {str(e)}")
        # Provide a fallback response if Gemini fails
        return {
            "title": f"Image: {filename}",
            "description": "No description available. Image analysis failed."
        }