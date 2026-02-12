import json
import sys

def inspect():
    try:
        with open('response.json', 'r') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error loading JSON: {e}")
        return

    choices = data.get('choices', [])
    if not choices:
        print("No choices found.")
        return

    choice = choices[0]
    message = choice.get('message', {})
    
    print("Message Keys:", message.keys())
    
    content = message.get('content', '')
    if content:
        print(f"Content Length: {len(content)}")
        print(f"Content Start: {content[:100]}")
    else:
        print("Content is empty/None.")
        
    reasoning = message.get('reasoning', '')
    if reasoning:
        print(f"Reasoning Length: {len(reasoning)}")
        
    images = message.get('images', [])
    if images:
        print(f"Images Found: {len(images)}")
        first_img = images[0]
        print(f"Image Type: {type(first_img)}")
        if isinstance(first_img, dict):
            print(f"Image Keys: {first_img.keys()}")
            if 'image_url' in first_img:
                img_url_obj = first_img['image_url']
                print(f"Prioritizing image_url: {type(img_url_obj)}")
                if isinstance(img_url_obj, dict):
                    print(f"Keys: {img_url_obj.keys()}")
                    if 'url' in img_url_obj:
                         url_val = img_url_obj['url']
                         print(f"URL Length: {len(url_val)}")
                         print(f"URL Start: {url_val[:50]}...")
        elif isinstance(first_img, str):
            print(f"Image Length: {len(first_img)}")
            print(f"Image Start: {first_img[:50]}...")
    else:
        print("No 'images' key found or empty.")

if __name__ == "__main__":
    inspect()
