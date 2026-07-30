import json
import pickle
import redis

def migrate():

    r = redis.Redis(host='localhost', port=6379, db=0,decode_responses=True)
    
    try:
        r.ping()
        print('Redis Up')
    except redis.ConnectionError:
        print('Cant connect to redis')
        return

    df = pickle.load(open('animes.pkl', 'rb'))
    pipe = r.pipeline()

    count =0

    for row_idx, row in df.iterrows():
        mal_id = int(row['MAL_ID'])

        metadata={
            "name": str(row['Name']),
            "desc": str(row['description']),
            "img_url": str(row['image'])
        }

        pipe.set(f'anime:{mal_id}', json.dumps(metadata))
        pipe.set(f"mal_to_idx:{mal_id}", row_idx)
        pipe.set(f"idx_to_mal:{row_idx}", mal_id)

        count +=1

        if count%1000 ==0:
            pipe.execute()
    
    pipe.execute()
    print('Donee migrating')

if __name__=='__main__':
    migrate()