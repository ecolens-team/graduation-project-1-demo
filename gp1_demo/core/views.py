import os
import torch
import open_clip
from PIL import Image
from django.shortcuts import render
from django.http import JsonResponse
from django.views import View
from django.core.files.storage import FileSystemStorage
from django.conf import settings

print("Loading BioClip Model")
device = "cpu"

model, _, preprocess = open_clip.create_model_and_transforms('hf-hub:imageomics/bioclip-2', device=device)
tokenizer = open_clip.get_tokenizer('hf-hub:imageomics/bioclip-2')

SPECIES_LABELS = [
    'black iris',
    'bee',
    'beetle',
]

text_tokens = tokenizer(SPECIES_LABELS)

class HomeView(View):
    def get(self, request):
        return render(request, 'core/home.html')

    def post(self, request):
        image_file = request.FILES.get('image')
        if not image_file:
            return render(request, 'core/home.html')

        # save on server locally
        fs = FileSystemStorage(location=os.path.join(settings.MEDIA_ROOT, 'observations'))
        filename = fs.save(image_file.name, image_file)
        file_url = f"{settings.MEDIA_URL}observations/{filename}"
        full_file_path = fs.path(filename)

        # run model
        try:
            pil_image = Image.open(full_file_path).convert("RGB")
            image = preprocess(pil_image).unsqueeze(0).to(device)
            
            with torch.no_grad():
                image_features = model.encode_image(image)
                image_features /= image_features.norm(dim=-1, keepdim=True)
                text_features = model.encode_text(text_tokens)
                text_features /= text_features.norm(dim=-1, keepdim=True)
                
                text_probs = (100.0 * image_features @ text_features.T).softmax(dim=-1)
            
            
            best_idx = text_probs.argmax().item()
            confidence = text_probs[0][best_idx].item()
            species_prediction = SPECIES_LABELS[best_idx]
            
        except Exception as e:
            print(f"Error: {e}")
            species_prediction = "Error processing image"
            confidence = 0.0

        return render(request, 'core/home.html', {
            'prediction': species_prediction,
            'confidence': f"{confidence:.1%}",
            'image_url': file_url
        })