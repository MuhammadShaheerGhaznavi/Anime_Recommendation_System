from contextlib import asynccontextmanager
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException, Depends,Request
# import pickle
import os
import faiss
# import pandas as pd
import redis
import json

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

class AnimeResponse(BaseModel):
    mal: int 
    name: str = 'NULL' # for now
    desc : str = "NULL"
    img_url: str = 'NULL'
    # similar_animes : list[int] = []

@app.get('/show_recommendations', response_model=list[AnimeResponse]) # Cant use request bodies (pydantic Model here) in GET input 
def recommend(
    mal_id: int, k:int = 10, r:redis.Redis = Depends(get_redis),
    index: faiss.Index = Depends(get_index)) -> list[AnimeResponse]:

    cache_key = f'anime:{mal_id}:{k}'
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

    recs = []
    _, I =  index.search(query, k +1) # accounting for the same anime
    for i in I[0]: ## I[0] returns the row positions in the index (NOT MAL IDs) of the most similar animes
         
        if i == row_idx: continue
        # cann get desc using anime_details.pkl .. is it something that's efficient --> just made a new file called animes.pkl that contains desc and urls
        malid = r.get(f'idx_to_mal:{i}')
        anime_meta = r.get(f'anime:{malid}')
        if anime_meta:
            meta = json.loads(anime_meta)
            obj = AnimeResponse(mal=int(malid), 
                            name=meta.get("name", "Unknown"),
                            desc=meta.get("desc", ""),
                            img_url=meta.get("img_url", "")
                        )
            recs.append(obj)
    serializable_recs = [rec.model_dump() for rec in recs]
    r.setex(cache_key, 86400, json.dumps(serializable_recs))
    return recs
    

         





