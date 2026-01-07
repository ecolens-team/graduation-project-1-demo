import os
import json
import torch
import open_clip
from PIL import Image
from django.shortcuts import render
from django.views import View
from django.core.files.storage import FileSystemStorage
from django.conf import settings
from django.contrib.auth.decorators import login_required
from core.models import Observation
from django.contrib.auth.mixins import LoginRequiredMixin

print("--- SERVER STARTUP ---")
device = "cpu"

#loading model
model, _, preprocess = open_clip.create_model_and_transforms('hf-hub:imageomics/bioclip', device=device)
tokenizer = open_clip.get_tokenizer('hf-hub:imageomics/bioclip')

#species lists
try:
    json_path = os.path.join(settings.BASE_DIR, 'species.json')
    with open(json_path, 'r') as f:
        data = json.load(f)
        SPECIES_LABELS = data.get('plants', []) + data.get('insects', [])
except Exception as e:
    print(f"Error loading JSON: {e}. Using fallback.")
    SPECIES_LABELS = ['black iris', 'bee', 'beetle']


CACHE_PATH = os.path.join(settings.BASE_DIR, 'species_embeddings.pt')
TEXT_FEATURES = None

TEMPLATES = [
    lambda c: f'a photo of a {c}.',
    lambda c: f'a close-up photo of a {c}.',
    lambda c: f'a photo of the {c}.',
    lambda c: f'the {c} in the wild.',
    lambda c: f'a specimen of {c}.',
    lambda c: f'it is a {c}.',
]

def load_or_compute_embeddings():
    global TEXT_FEATURES
    
    #load cached embeddings if they exist
    if os.path.exists(CACHE_PATH):
        print(f"Found cached embeddings at {CACHE_PATH}...")
        try:
            cached_data = torch.load(CACHE_PATH, weights_only=True)
            if cached_data.shape[1] == len(SPECIES_LABELS):
                return cached_data.to(device)
            else:
                print(f"Cache mismatch (Saved: {cached_data.shape[1]}, Current: {len(SPECIES_LABELS)}). Recomputing...")
        except Exception as e:
            print(f"Corrupt cache: {e}. Recomputing...")

    print(f"Computing embeddings for {len(SPECIES_LABELS)} species...")
    
    with torch.no_grad():
        all_features = []
        for i, species_name in enumerate(SPECIES_LABELS):
            if i % 100 == 0: print(f"Processing {i}/{len(SPECIES_LABELS)}...")

            texts = [template(species_name) for template in TEMPLATES]
            tokens = tokenizer(texts)
            class_embeddings = model.encode_text(tokens)
            class_embeddings /= class_embeddings.norm(dim=-1, keepdim=True)

            class_embedding = class_embeddings.mean(dim=0)
            class_embedding /= class_embedding.norm()
            all_features.append(class_embedding)

        features_matrix = torch.stack(all_features, dim=1).to(device)
        
        torch.save(features_matrix, CACHE_PATH)
        print(f"Saved embeddings to {CACHE_PATH}")
        
        return features_matrix


TEXT_FEATURES = load_or_compute_embeddings()
print("--- AI READY ---")


class UploadView(LoginRequiredMixin, View):
    def get(self, request):
        return render(request, 'core/upload.html')

    def post(self, request):
        image_file = request.FILES.get('image')
        if not image_file:
            return render(request, 'core/upload.html')

        fs = FileSystemStorage(location=os.path.join(settings.MEDIA_ROOT, 'observations'))
        filename = fs.save(image_file.name, image_file)
        file_url = f"{settings.MEDIA_URL}observations/{filename}"
        full_file_path = fs.path(filename)

        try:
            pil_image = Image.open(full_file_path).convert("RGB")
            image = preprocess(pil_image).unsqueeze(0).to(device)
            
            with torch.no_grad():
                image_features = model.encode_image(image)
                image_features /= image_features.norm(dim=-1, keepdim=True)

                text_probs = (100.0 * image_features @ TEXT_FEATURES).softmax(dim=-1)
            
            best_idx = text_probs.argmax().item()
            confidence = text_probs[0][best_idx].item()
            species_prediction = SPECIES_LABELS[best_idx]
            
        except Exception as e:
            print(f"Error: {e}")
            species_prediction = "Error processing image"
            confidence = 0.0

        Observation.objects.create(
            user=request.user,
            image=f'observations/{filename}',
            species_name=species_prediction,
            confidence=confidence*100
        )

        return render(request, 'core/upload.html', {
            'prediction': species_prediction,
            'confidence': f"{confidence:.1%}",
            'image_url': file_url
        })


class HomeView(LoginRequiredMixin, View):
    def get(self, request):
        observations = Observation.objects.all().order_by('-created_at')
        return render(request, 'core/home.html', {'observations': observations})

