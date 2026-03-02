"""
AI Image Generation for Author Social Calendar
Creates professional social media images from text descriptions using DALL-E
"""
import os
import logging
import requests
import base64
from io import BytesIO
from PIL import Image
import openai

logger = logging.getLogger(__name__)

class ImageGenerator:
    def __init__(self):
        self.client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        
    def create_social_media_image(self, image_idea, book_title, post_theme="social_media", style="children's book", timeout=60, hook="", brand_assets=None):
        """
        Generate a professional social media image from a text description
        
        Args:
            image_idea: The text description of what the image should show
            book_title: The book title to incorporate if needed
            post_theme: Type of post (value, bts, quote, engagement, promo)
            style: Visual style to apply
            timeout: Request timeout in seconds (default 60)
            hook: Hook text to overlay at the top of the image
            brand_assets: Dictionary containing brand colors, fonts, and asset paths
        """
        try:
            # Set timeout for OpenAI client
            self.client.timeout = timeout
            
            # Check if this is a cover reveal post
            is_cover_reveal = 'cover reveal' in image_idea.lower() or 'cover reveal' in hook.lower()
            
            if is_cover_reveal and brand_assets and brand_assets.get('book_cover_path'):
                logger.info("📚 Detected cover reveal post - creating clean book cover showcase")
                return self._create_cover_reveal_image(brand_assets, hook)
            
            # Extract brand colors if provided
            brand_colors = ""
            if brand_assets:
                primary = brand_assets.get('primary_color', '')
                secondary = brand_assets.get('secondary_color', '')
                background = brand_assets.get('background_color', '')
                
                if primary or secondary or background:
                    brand_colors = f"\nBrand colors to incorporate: "
                    if primary:
                        brand_colors += f"primary {primary}, "
                    if secondary:
                        brand_colors += f"secondary {secondary}, "
                    if background:
                        brand_colors += f"background {background}"
                    brand_colors = brand_colors.rstrip(', ')
                    logger.info(f"🎨 Adding brand colors to prompt: {brand_colors.strip()}")
                else:
                    logger.warning("⚠️  No brand colors provided in brand_assets")
            else:
                logger.warning("⚠️  No brand_assets provided to image generator")
            
            # Create a detailed prompt optimized for children's book marketing
            style_modifiers = {
                'value': 'warm, educational, family-friendly',
                'bts': 'behind-the-scenes, authentic, creative process',
                'quote': 'inspirational, text-overlay friendly, calming',
                'engagement': 'inviting, community-focused, interactive',
                'promo': 'eye-catching, professional, marketing-focused'
            }
            
            style_mod = style_modifiers.get(post_theme, 'professional')
            
            # Design treatments for visual variety - rotate through 10 different styles
            design_treatments = [
                {
                    'name': 'minimalist_centered',
                    'description': 'Clean minimalist design with subject centered on solid color background',
                    'prompt': f'Minimalist composition with central subject on solid {brand_colors} background, ample negative space, modern and clean'
                },
                {
                    'name': 'bold_border',
                    'description': 'Bold colored border frame around the main image',
                    'prompt': f'Bold decorative border frame using {brand_colors} around the image edges (40px thick), create visual containment'
                },
                {
                    'name': 'geometric_shapes',
                    'description': 'Geometric shapes and patterns as design elements',
                    'prompt': f'Geometric circles, triangles, or rectangles as design accents using {brand_colors}, modern playful layout'
                },
                {
                    'name': 'gradient_overlay',
                    'description': 'Soft gradient color overlay',
                    'prompt': f'Soft gradient overlay transitioning between {brand_colors}, dreamy and atmospheric'
                },
                {
                    'name': 'split_layout',
                    'description': 'Split screen with color block on one side',
                    'prompt': f'Split composition with solid {brand_colors} color block on left 30% and image on right 70%, modern editorial style'
                },
                {
                    'name': 'organic_frame',
                    'description': 'Organic hand-drawn frame or border',
                    'prompt': f'Hand-drawn organic frame or border elements in {brand_colors}, whimsical and friendly'
                },
                {
                    'name': 'color_splash',
                    'description': 'Strategic color splashes and accents',
                    'prompt': f'Strategic color splashes or paint strokes in {brand_colors} as artistic accents, energetic and creative'
                },
                {
                    'name': 'layered_shapes',
                    'description': 'Layered abstract shapes in background',
                    'prompt': f'Layered abstract shapes in background using {brand_colors}, create depth and visual interest'
                },
                {
                    'name': 'corner_accent',
                    'description': 'Decorative corner elements',
                    'prompt': f'Decorative corner flourishes or design elements in {brand_colors} (top-left and bottom-right), elegant framing'
                },
                {
                    'name': 'textured_background',
                    'description': 'Textured or patterned background',
                    'prompt': f'Subtle textured or patterned background in {brand_colors} (watercolor, paper texture, or soft pattern), adds depth'
                }
            ]
            
            # Deterministic design treatment selection using content hash
            # This ensures visual variety across posts while maintaining consistency 
            # if the same content is regenerated (same image_idea + book_title = same treatment)
            import hashlib
            design_index = int(hashlib.md5(f"{image_idea}{book_title}".encode()).hexdigest(), 16) % len(design_treatments)
            selected_treatment = design_treatments[design_index]
            
            logger.info(f"🎨 Selected design treatment ({design_index + 1}/10): {selected_treatment['name']}")
            
            enhanced_prompt = f"""
            Create a professional social media image for a children's book marketing campaign.
            
            Image concept: {image_idea}
            Book: {book_title}
            Style: {style_mod}, children's book illustration style, warm colors, family-friendly
            
            DESIGN TREATMENT: {selected_treatment['prompt']}
            
            Color Requirements:
            {brand_colors if brand_colors else "Use warm, inviting colors suitable for children's literature"}
            - Use brand colors strategically in borders, backgrounds, accents, and design elements
            - Ensure brand colors are prominent and visible in the composition
            - Create cohesive color harmony between brand colors and illustration
            
            Layout Requirements:
            - High quality, professional 1024x1024 square format for Instagram
            - Position main subjects (faces, people, key elements) in CENTER or UPPER 60% of image
            - Keep BOTTOM 25% clear or minimal detail for text overlay space
            - Create visual variety through the design treatment style
            
            ⚠️ CRITICAL RESTRICTIONS:
            - DO NOT include any text, letters, words, or typography in the image
            - NO book titles, NO quotes, NO captions, NO labels
            - DO NOT show books, book covers, or pages with the title "{book_title}" visible
            - DO NOT depict the physical book product itself
            - Focus on the CONCEPT or THEME of the post, not the book object
            - ONLY visual elements - illustrations, graphics, patterns, and designs
            - All text will be added later programmatically
            
            Quality Standards:
            - Child-safe, wholesome, and inviting aesthetic
            - Professional marketing quality with strong visual impact
            - Instagram-ready composition that stands out in a grid
            """
            
            logger.info(f"Generating image for: {image_idea[:50]}...")
            
            response = self.client.images.generate(
                model="dall-e-3",
                prompt=enhanced_prompt,
                size="1024x1024",
                quality="standard",
                n=1
            )
            
            # Get the image URL
            if not response.data or len(response.data) == 0:
                raise ValueError("No image data returned from DALL-E")
            
            image_url = response.data[0].url
            
            if not image_url:
                raise ValueError("No image URL returned from DALL-E")
            
            # Download the image
            image_response = requests.get(image_url)
            image_response.raise_for_status()
            
            # Load the generated image for potential compositing
            generated_image = Image.open(BytesIO(image_response.content))
            
            # Composite uploaded assets if available
            if brand_assets:
                book_cover_path = brand_assets.get('book_cover_path')
                author_photo_path = brand_assets.get('author_photo_path')
                
                # For BTS posts, try to composite author photo
                if author_photo_path and post_theme == 'bts':
                    try:
                        generated_image = self._composite_author_photo(generated_image, author_photo_path)
                        logger.info("Composited author photo onto generated image")
                    except Exception as e:
                        logger.warning(f"Failed to composite author photo: {str(e)}")
                
                # For promo/value posts, try to composite book cover
                elif book_cover_path and post_theme in ['promo', 'value', 'quote']:
                    try:
                        generated_image = self._composite_book_cover(generated_image, book_cover_path)
                        logger.info("Composited book cover onto generated image")
                    except Exception as e:
                        logger.warning(f"Failed to composite book cover: {str(e)}")
            
            # Overlay hook text if provided
            if hook and hook.strip():
                try:
                    generated_image = self._overlay_hook_text(generated_image, hook, brand_assets)
                    logger.info(f"Overlaid hook text: {hook[:30]}...")
                except Exception as e:
                    logger.warning(f"Failed to overlay hook text: {str(e)}")
            
            # Save to static/images for public access with unique filename
            import uuid
            from datetime import datetime
            
            # Generate unique filename with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            unique_id = str(uuid.uuid4())[:8]
            filename = f"social_{timestamp}_{unique_id}.png"
            filepath = os.path.join('static', 'images', filename)
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            # Save the final composited image
            generated_image.save(filepath, format='PNG')
            logger.info(f"Saved image to: {filepath}")
            
            # Create public URL (relative path for Flask static files)
            public_url = f"/static/images/{filename}"
            
            # Convert to base64 for easy storage/display
            buffer = BytesIO()
            generated_image.save(buffer, format='PNG')
            image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            
            return {
                'success': True,
                'image_url': public_url,  # Now returns permanent static URL
                'dalle_url': image_url,  # Original DALL-E URL (temporary)
                'image_base64': image_base64,
                'filepath': filepath,  # Local file path for tracking
                'size': '1024x1024',
                'format': 'PNG'
            }
            
        except Exception as e:
            logger.error(f"Image generation failed: {str(e)}", exc_info=True)
            error_msg = str(e)
            
            # Provide more helpful error messages
            if "timeout" in error_msg.lower():
                error_msg = "Image generation timed out. Please try again with a simpler image description."
            elif "rate limit" in error_msg.lower():
                error_msg = "OpenAI rate limit reached. Please wait a moment and try again."
            
            return {
                'success': False,
                'error': error_msg,
                'fallback_suggestion': 'Consider using a stock photo or creating a text-only post'
            }
    
    def create_multiple_formats(self, image_idea, book_title, post_theme="social_media"):
        """
        Generate images in multiple social media formats
        Instagram Square (1080x1080), Facebook Wide (1200x630), Pinterest Tall (735x1102)
        """
        formats = {
            'instagram': '1024x1024',
            'facebook': '1024x1024',  # DALL-E only supports square, we'll crop later
            'pinterest': '1024x1024'  # DALL-E only supports square, we'll extend later
        }
        
        results = {}
        
        # Generate base image
        base_result = self.create_social_media_image(image_idea, book_title, post_theme)
        
        if base_result['success']:
            # For now, return the same image for all formats
            # In a future update, we could resize/crop for different platforms
            for platform, size in formats.items():
                results[platform] = base_result.copy()
                results[platform]['platform'] = platform
                results[platform]['optimized_size'] = size
        else:
            results['error'] = base_result
            
        return results
    
    def _composite_book_cover(self, background_image, book_cover_path):
        """Composite a book cover onto the generated background image."""
        # Open the book cover
        book_cover = Image.open(book_cover_path)
        
        # Calculate size - book cover should be about 30% of image width
        target_width = int(background_image.width * 0.3)
        aspect_ratio = book_cover.height / book_cover.width
        target_height = int(target_width * aspect_ratio)
        
        # Resize book cover
        book_cover = book_cover.resize((target_width, target_height), Image.Resampling.LANCZOS)
        
        # Position: bottom-right corner with some padding
        x = background_image.width - target_width - 50
        y = background_image.height - target_height - 50
        
        # Composite with transparency if available
        if book_cover.mode == 'RGBA':
            background_image.paste(book_cover, (x, y), book_cover)
        else:
            background_image.paste(book_cover, (x, y))
        
        return background_image
    
    def _composite_author_photo(self, background_image, author_photo_path):
        """Composite an author photo onto the generated background image."""
        # Open the author photo
        author_photo = Image.open(author_photo_path)
        
        # Create circular mask for author photo
        target_size = int(background_image.width * 0.25)
        author_photo = author_photo.resize((target_size, target_size), Image.Resampling.LANCZOS)
        
        # Create circular mask
        mask = Image.new('L', (target_size, target_size), 0)
        from PIL import ImageDraw
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0, target_size, target_size), fill=255)
        
        # Convert to RGBA if needed
        if author_photo.mode != 'RGBA':
            author_photo = author_photo.convert('RGBA')
        
        # Apply circular mask
        output = Image.new('RGBA', (target_size, target_size), (0, 0, 0, 0))
        output.paste(author_photo, (0, 0))
        output.putalpha(mask)
        
        # Position: top-right corner
        x = background_image.width - target_size - 50
        y = 50
        
        # Convert background to RGBA if needed
        if background_image.mode != 'RGBA':
            background_image = background_image.convert('RGBA')
        
        # Composite
        background_image.paste(output, (x, y), output)
        
        return background_image
    
    def _overlay_hook_text(self, background_image, hook_text, brand_assets=None):
        """Overlay hook text at the top of the image using brand fonts with dynamic sizing."""
        from PIL import ImageDraw, ImageFont
        
        # Get brand font and colors
        heading_font_name = brand_assets.get('heading_font', 'Playfair Display') if brand_assets else 'Playfair Display'
        primary_color = brand_assets.get('primary_color', '#FFFFFF') if brand_assets else '#FFFFFF'
        
        # Convert hex color to RGB
        def hex_to_rgb(hex_color):
            hex_color = hex_color.lstrip('#')
            return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        
        text_color = hex_to_rgb(primary_color)
        
        # Start with larger font and reduce if text is too long
        max_font_size = 70
        min_font_size = 35
        max_width = background_image.width - 100  # 50px padding on each side
        max_lines = 3  # Allow up to 3 lines
        
        # Function to wrap text and calculate dimensions
        def wrap_text_with_font(text, font, max_width):
            words = text.split()
            lines = []
            current_line = []
            temp_draw = ImageDraw.Draw(Image.new('RGBA', (1, 1)))
            
            for word in words:
                test_line = ' '.join(current_line + [word])
                bbox = temp_draw.textbbox((0, 0), test_line, font=font)
                text_width = bbox[2] - bbox[0]
                
                if text_width <= max_width:
                    current_line.append(word)
                else:
                    if current_line:
                        lines.append(' '.join(current_line))
                    current_line = [word]
            
            if current_line:
                lines.append(' '.join(current_line))
            
            return lines
        
        # Try different font sizes to find the best fit
        font_size = max_font_size
        font = None
        lines = []
        
        while font_size >= min_font_size:
            try:
                # Try to load DejaVu Sans Bold
                try:
                    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
                except:
                    font = ImageFont.load_default()
                    font_size = min(font_size, 40)
                
                lines = wrap_text_with_font(hook_text, font, max_width)
                
                # If text fits in max_lines or fewer, we're good
                if len(lines) <= max_lines:
                    break
                
                # Otherwise, try smaller font
                font_size -= 5
            except Exception as e:
                logger.warning(f"Font loading issue: {str(e)}")
                break
        
        # If still too many lines, truncate
        if len(lines) > max_lines:
            lines = lines[:max_lines]
            # Add ellipsis to last line if truncated
            if len(lines[-1]) > 40:
                lines[-1] = lines[-1][:40] + '...'
        
        # Calculate text block height
        line_height = font_size + 12
        total_text_height = len(lines) * line_height
        
        # Add semi-transparent background for better readability
        padding = 35
        bg_height = total_text_height + (padding * 2)
        
        # Position text at BOTTOM of image to avoid covering important visual elements
        bg_top = background_image.height - bg_height
        
        overlay = Image.new('RGBA', background_image.size, (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        
        # Draw semi-transparent background at bottom
        overlay_draw.rectangle(
            [(0, bg_top), (background_image.width, background_image.height)],
            fill=(0, 0, 0, 150)  # Semi-transparent black
        )
        
        # Composite the overlay
        if background_image.mode != 'RGBA':
            background_image = background_image.convert('RGBA')
        background_image = Image.alpha_composite(background_image, overlay)
        
        # Draw text at bottom
        draw = ImageDraw.Draw(background_image)
        
        # Draw each line centered at bottom
        y_position = bg_top + padding
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            text_width = bbox[2] - bbox[0]
            x_position = (background_image.width - text_width) // 2
            
            # Draw text with white color for visibility
            draw.text((x_position, y_position), line, font=font, fill=(255, 255, 255, 255))
            y_position += line_height
        
        return background_image
    
    def _create_cover_reveal_image(self, brand_assets, hook):
        """
        Create a clean, professional cover reveal image with minimal background
        Shows the book cover large and centered without busy DALL-E backgrounds
        """
        try:
            from PIL import ImageDraw
            import uuid
            from datetime import datetime
            
            book_cover_path = brand_assets.get('book_cover_path')
            if not book_cover_path or not os.path.exists(book_cover_path):
                raise ValueError("Book cover not found")
            
            # Load book cover
            book_cover = Image.open(book_cover_path)
            if book_cover.mode != 'RGBA':
                book_cover = book_cover.convert('RGBA')
            
            # Create 1024x1024 canvas with gradient background
            canvas_size = 1024
            canvas = Image.new('RGBA', (canvas_size, canvas_size))
            
            # Create gradient background using brand colors
            primary = brand_assets.get('primary_color', '#F4F2F0')
            background = brand_assets.get('background_color', '#FFFFFF')
            
            # Parse hex colors
            def hex_to_rgb(hex_color):
                hex_color = hex_color.lstrip('#')
                return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
            
            try:
                color1 = hex_to_rgb(background)
                color2 = hex_to_rgb(primary)
            except:
                color1 = (244, 242, 240)
                color2 = (255, 255, 255)
            
            # Create vertical gradient
            for y in range(canvas_size):
                ratio = y / canvas_size
                r = int(color1[0] * (1 - ratio) + color2[0] * ratio)
                g = int(color1[1] * (1 - ratio) + color2[1] * ratio)
                b = int(color1[2] * (1 - ratio) + color2[2] * ratio)
                for x in range(canvas_size):
                    canvas.putpixel((x, y), (r, g, b, 255))
            
            # Calculate book cover size (70% of canvas width for prominence)
            cover_width = int(canvas_size * 0.7)
            aspect_ratio = book_cover.height / book_cover.width
            cover_height = int(cover_width * aspect_ratio)
            
            # Resize book cover maintaining aspect ratio
            book_cover_resized = book_cover.resize((cover_width, cover_height), Image.Resampling.LANCZOS)
            
            # Center the book cover vertically and horizontally
            x_position = (canvas_size - cover_width) // 2
            y_position = (canvas_size - cover_height) // 2
            
            # Add subtle drop shadow
            shadow = Image.new('RGBA', canvas.size, (0, 0, 0, 0))
            shadow_draw = ImageDraw.Draw(shadow)
            shadow_offset = 10
            shadow_draw.rectangle(
                [
                    (x_position + shadow_offset, y_position + shadow_offset),
                    (x_position + cover_width + shadow_offset, y_position + cover_height + shadow_offset)
                ],
                fill=(0, 0, 0, 80)
            )
            from PIL import ImageFilter
            shadow = shadow.filter(ImageFilter.GaussianBlur(15))
            canvas = Image.alpha_composite(canvas, shadow)
            
            # Paste book cover onto canvas
            canvas.paste(book_cover_resized, (x_position, y_position), book_cover_resized)
            
            # Overlay hook text if provided
            if hook and hook.strip():
                canvas = self._overlay_hook_text(canvas, hook, brand_assets)
                logger.info(f"Overlaid hook text on cover reveal: {hook[:30]}...")
            
            # Save to static/images
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            unique_id = str(uuid.uuid4())[:8]
            filename = f"cover_reveal_{timestamp}_{unique_id}.png"
            filepath = os.path.join('static', 'images', filename)
            
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            canvas.save(filepath, format='PNG')
            logger.info(f"✨ Saved clean cover reveal image to: {filepath}")
            
            # Create public URL
            public_url = f"/static/images/{filename}"
            
            # Convert to base64
            buffer = BytesIO()
            canvas.save(buffer, format='PNG')
            image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            
            return {
                'success': True,
                'image_url': public_url,
                'dalle_url': None,  # No DALL-E used for cover reveals
                'image_base64': image_base64,
                'filepath': filepath,
                'size': '1024x1024',
                'format': 'PNG'
            }
            
        except Exception as e:
            logger.error(f"Failed to create cover reveal image: {str(e)}")
            raise
    
    def optimize_for_platform(self, image_base64, platform='instagram'):
        """
        Optimize image dimensions for specific social media platforms
        """
        try:
            # Decode base64 image
            image_data = base64.b64decode(image_base64)
            image = Image.open(BytesIO(image_data))
            
            # Platform-specific optimizations
            if platform == 'instagram':
                # Instagram prefers 1080x1080
                target_size = (1080, 1080)
            elif platform == 'facebook':
                # Facebook shared images work well at 1200x630
                target_size = (1200, 630) 
            elif platform == 'pinterest':
                # Pinterest prefers tall images 735x1102
                target_size = (735, 1102)
            else:
                target_size = (1080, 1080)  # Default square
            
            # For now, just resize while maintaining aspect ratio
            # In future, could add smart cropping or padding
            image.thumbnail(target_size, Image.Resampling.LANCZOS)
            
            # Convert back to base64
            buffer = BytesIO()
            image.save(buffer, format='PNG')
            optimized_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            
            return {
                'success': True,
                'image_base64': optimized_base64,
                'size': f"{image.width}x{image.height}",
                'platform': platform
            }
            
        except Exception as e:
            logger.error(f"Image optimization failed: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

# Global instance
image_generator = ImageGenerator()

def generate_single_image(post_data, brand_assets=None):
    """
    Generate a single image for a post.
    
    Args:
        post_data: Dict with 'hook', 'theme', 'image_idea', 'caption'
        brand_assets: Dict with brand colors, fonts, and asset paths
        
    Returns:
        Dict with 'image_url' and 'image_path' or None on failure
    """
    try:
        hook = post_data.get('hook', '')
        theme = post_data.get('theme', 'value')
        image_idea = post_data.get('image_idea', post_data.get('caption', ''))
        book_title = brand_assets.get('book_title', 'Book') if brand_assets else 'Book'
        
        logger.info(f"Generating single image for {theme} post: {hook[:50]}...")
        
        result = image_generator.create_social_media_image(
            image_idea=image_idea,
            book_title=book_title,
            post_theme=theme,
            hook=hook,
            brand_assets=brand_assets
        )
        
        if result and result.get('success'):
            return {
                'image_url': result.get('image_url', ''),
                'image_path': result.get('image_path', '')
            }
        else:
            logger.error(f"Failed to generate image: {result.get('error', 'Unknown error')}")
            return None
            
    except Exception as e:
        logger.error(f"Error in generate_single_image: {str(e)}", exc_info=True)
        return None