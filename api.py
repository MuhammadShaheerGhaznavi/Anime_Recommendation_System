from contextlib import asynccontextmanager
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException, Depends,Request
# import pickle
import os
import faiss
from fastapi.middleware.cors import CORSMiddleware
import redis
import json
from typing import Optional

def get_redis(request : Request) -> redis.Redis:
    return request.app.state.redis # why do we need request object here

def get_index(request: Request) -> faiss.Index:
    return request.app.state.index



@asynccontextmanager
async def lifespan(app: FastAPI):

    if not os.path.exists('anime_vector.index'):
        raise FileNotFoundError
    
    print('Starting!!')

    app.state.redis = redis.Redis(host='localhost',
                                  port=6379,
                                  db= 0,
                                  decode_responses=True)
    app.state.index = faiss.read_index('anime_vector.index')

    yield ## why do I needd this??
    print('Shutting Down!!')

    app.state.redis.close()
    del app.state.index


app = FastAPI(
    title='Anime Recommendation API',
    lifespan= lifespan)

# Enable CORS for cross-origin frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AnimeResponse(BaseModel):
    mal: int 
    name: str = 'NULL' # for now
    desc : str = "NULL"
    img_url: str = 'NULL'
    # similar_animes : list[int] = []

class AnimeDetailResponse(BaseModel):
    mal_id: int
    name: str = 'Unknown'
    desc: str = ''
    img_url: str = ''
    score: Optional[float] =None
    mal_url: Optional[str] = None
    gallery: list[str] = []

@app.get('/animes', response_model=dict[str,int])
def get_anime_list(r:redis.Redis= Depends(get_redis))->dict[str, int]:
    cached_map = r.get("anime_titles_map")
    if cached_map:
        return json.loads(cached_map)
    
    raise HTTPException(
        status_code=404, 
        detail="Anime titles mapping not found."
    )

@app.get('/anime/{mal_id}', response_model=AnimeDetailResponse)
def get_anime_details(mal_id:int, r:redis.Redis= Depends(get_redis))->AnimeDetailResponse:
    raw_meta = r.get(f"anime:{mal_id}")
    if not raw_meta:
        raise HTTPException(status_code=404, detail="Anime details not found")
    
    meta = json.loads(raw_meta)
    return AnimeDetailResponse(
        mal_id=int(meta.get("mal_id", mal_id)),
        name=meta.get("name", "Unknown"),
        desc=meta.get("desc", ""),
        img_url=meta.get("img_url", ""),
        score=meta.get("score"),
        mal_url=meta.get("url"),
        gallery=meta.get("gallery", [])
    )

@app.get('/show_recommendations', response_model=list[AnimeResponse]) # Cant use request bodies (pydantic Model here) in GET input 
def recommend(
    mal_id: int, k:int = 10, min_rating:float =0.0, no_same: bool = False,r:redis.Redis = Depends(get_redis),
    index: faiss.Index = Depends(get_index)) -> list[AnimeResponse]:

    cache_key = f'anime:{mal_id}:{k}:{min_rating}:{no_same}'
    cached_recs= r.get(cache_key)
    if cached_recs:
        print('Cache Hit!')
        return [AnimeResponse(**item) for item in json.loads(cached_recs)]
    ## json.loads() converts a JSON-formatted string into a Python object, which will be a dictionary if the root of the JSON data is a JSON object
    ## Serialization is the process of converting a Python object into a stream of bytes or a string format so it can be saved to a file or transmitted over a network. Conversely, deserialization is the reverse process
    
    print('Cache Miss!')

    row_idx = r.get(f'mal_to_idx:{mal_id}')
    if not row_idx:
        raise HTTPException(status_code=404, detail= "MAL ID not in dataset")
    row_idx = int(row_idx)
    query = index.reconstruct(row_idx).reshape(1,-1).astype('float32')

    target_raw_meta = r.get(f'anime:{mal_id}')
    target_name = json.loads(target_raw_meta).get('name','').lower() if target_raw_meta else ""

    fetch_count = max(k*4, 50)
    _,I = index.search(query, fetch_count)
    neighbor_indices = [int(i) for i in I[0] if i != row_idx and i != -1] # index returns -1, if there are not enough vectors etc
    if not neighbor_indices: return []

    # mget to do batch query
    idx_keys = [f"idx_to_mal:{i}" for i in neighbor_indices]
    fetched_mal_ids = r.mget(idx_keys)

    meta_keys = [f"anime:{mal}" for mal in fetched_mal_ids if mal]
    if not meta_keys: return []
    raw_metas = r.mget(meta_keys)
    
        
    recs = []
    for raw_meta in raw_metas:
        if not raw_meta or len(recs)>= k: continue
        meta = json.loads(raw_meta)
        rec_name = meta.get('name','')
        rec_score = meta.get('score')

        if min_rating>0.0 and (rec_score is None or rec_score< min_rating): continue
        if no_same and target_name and (target_name in rec_name.lower() or rec_name.lower() in target_name):
            continue
        recs.append(AnimeResponse(
            mal=int(meta.get("mal_id", -1)),
            name=rec_name,
            desc=meta.get("desc", ""),
            img_url=meta.get("img_url", ""),
        ))
        # Cache this key

    serializable_recs = [rec.model_dump() for rec in recs]
    r.setex(cache_key, 86400, json.dumps(serializable_recs))

    return recs
