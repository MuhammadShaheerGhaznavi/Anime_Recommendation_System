import json
import pickle
import redis


def load_multi_pickle(filename: str) -> dict:
    """Helper to unpickle files that contain multiple dictionary chunks."""
    result = {}
    with open(filename, "rb") as f:
        while True:
            try:
                result.update(pickle.load(f))
            except EOFError:
                break
    return result


def migrate():
    r = redis.Redis(host="127.0.0.1", port=6379, db=0, decode_responses=True)

    try:
        r.ping()
        print("Redis connection successful!")
    except redis.ConnectionError:
        print("Could not connect to Redis. Ensure Docker or local Redis is running.")
        return

    # 1. Load all pickle datasets
    df = pickle.load(open("animes.pkl", "rb"))
    gallery_data = load_multi_pickle("anime_gallery.pkl")
    details_data = load_multi_pickle("anime_details.pkl")

    pipe = r.pipeline()
    count = 0
    anime_titles_map = {}

    for row_idx, row in df.iterrows():
        mal_id = int(row["MAL_ID"])
        anime_name = str(row["Name"])

        # Populate the Name -> MAL ID dictionary for the GET /animes dropdown endpoint
        anime_titles_map[anime_name] = mal_id

        # Safely fetch gallery list (checking both int and str key formats)
        gallery_urls = gallery_data.get(mal_id) or gallery_data.get(str(mal_id)) or []

        # Safely fetch detailed metadata dictionary
        item_details = details_data.get(mal_id) or details_data.get(str(mal_id)) or {}

        # Extract trailer URL safely (checking both direct url and youtube embed_url)
        trailer_dict = item_details.get("trailer") or {}
        trailer_url = trailer_dict.get("url") or trailer_dict.get("embed_url")

        metadata = {
            "mal_id": mal_id,
            "name": anime_name,
            "desc": str(row.get("description", "")),
            "img_url": str(row.get("image", "")),
            "gallery": gallery_urls,
            "score": item_details.get("score"),
            "url": item_details.get("url"),
            "trailer_url": trailer_url,
        }

        # Queue Redis commands
        pipe.set(f"anime:{mal_id}", json.dumps(metadata))
        pipe.set(f"mal_to_idx:{mal_id}", row_idx)
        pipe.set(f"idx_to_mal:{row_idx}", mal_id)

        count += 1

        if count % 1000 == 0:
            pipe.execute()

    # Store the complete title mapping required by GET /animes
    pipe.set("anime_titles_map", json.dumps(anime_titles_map))

    # Execute remaining commands in pipeline
    pipe.execute()

    print(f"Successfully migrated {count} records, gallery, score, and URL metadata to Redis!")


if __name__ == "__main__":
    migrate()