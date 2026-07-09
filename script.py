import pickle as pkl
import requests
import time
import os 

# 1. LOAD CHECKPOINTS FIRST (Before opening any files for writing)
mal_collected_set = set()
if os.path.exists('checkpoints.pkl'):
    try:
        with open('checkpoints.pkl', 'rb') as check:
            checkpoints = pkl.load(check)
            mal_collected_set.update(checkpoints)  # Fix: use .update() to merge sets
            print(f"Resuming from checkpoint. {len(mal_collected_set)} animes already processed.")
    except (EOFError, pkl.UnpicklingError):
        pass  # Handles case where checkpoint file exists but is empty/corrupt

# Load target list
animes = pkl.load(open('anime_list.pkl', 'rb'))
mal_ids = animes['MAL_ID']

mal_pending_set = set()
mal_err_set = set()
count = 0

# 2. OPEN DATA FILES (Removed checkpoints.pkl from the global context to avoid locking/truncation)
with open('anime_details.pkl', 'ab') as file, open('anime_gallery.pkl', 'ab') as file2:
    for mal in mal_ids:
        
        if mal in mal_collected_set:
            continue

        current_details = None  # Temporary holder so we only save if the whole loop passes

        # --- STEP 1: FETCH DETAILS ---
        try: 
            url = f"https://api.jikan.moe/v4/anime/{mal}/full"
            details = requests.get(url, timeout=8)

            if details.status_code == 429: # rate limited
                print("being rate limited on details")
                mal_pending_set.add(mal)
                time.sleep(15)
                continue
            elif details.status_code == 404:
                print(f"{mal} not found .. skipping it")
                mal_collected_set.add(mal)
                continue
            elif details.status_code not in [200, 404, 429]:
                err = details.json()
                mal_err_set.add(mal)
                continue
            else:
                current_details = details.json().get('data', {})

        except requests.RequestException:
            continue
        
        time.sleep(1)  # Respecting Jikan's rate limits

        # --- STEP 2: FETCH PICTURES ---
        try:
            url = f"https://api.jikan.moe/v4/anime/{mal}/pictures"
            pics = requests.get(url, timeout=8)

            if pics.status_code == 429:
                print("being rate limited on pictures")
                mal_pending_set.add(mal)
                time.sleep(15)
                continue
            elif pics.status_code == 404:
                print(f"{mal} pictures not found .. skipping")
                # If details worked but pictures 404'd, save what we have and mark complete
                if current_details:
                    pkl.dump({f'{mal}': current_details}, file)
                mal_collected_set.add(mal)
                continue
            elif pics.status_code not in [200, 404, 429]:
                err = pics.json()
                mal_err_set.add(mal)
                continue
            else:
                data = pics.json().get('data', [])
                img_list = []
                for img in data:
                    if img.get('jpg'):
                        img_list.append(img['jpg']['large_image_url'])
                
                # BOTH SUCCESSFUL: Commit data to both pickles safely
                if current_details:
                    pkl.dump({f'{mal}': current_details}, file)
                pkl.dump({f'{mal}': img_list}, file2)
                
                mal_collected_set.add(mal)
                count += 1

        except requests.RequestException:
            continue 

        # 3. SAVE CHECKPOINT (Triggers every 500 successful iterations)
        if count > 0 and count % 500 == 0:
            with open('checkpoints.pkl', 'wb') as check_f:
                pkl.dump(mal_collected_set, check_f)
            print(f"Checkpoint saved at {count} new items! Total processed: {len(mal_collected_set)}")

        time.sleep(1)