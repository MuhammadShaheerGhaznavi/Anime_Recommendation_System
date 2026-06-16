import pickle
import streamlit as st
import requests

def fetch_poster(MAL_ID):
    print(MAL_ID)
    jikan_url = "https://api.jikan.moe/v4/anime/{}/pictures".format(MAL_ID)
    data = requests.get(jikan_url)
    data = data.json()
    # print(data)
    try:
        poster_url = data['data'][0]["jpg"]["large_image_url"]
    except KeyError:
        return False
    
    return poster_url

def recommend(anime):
    index = animes[animes['Name'] ==anime].index[0]
    distances = sorted(list(enumerate(similarity[index])),reverse=True, key = lambda x:x[1])
    recommended_animes = []
    recommended_anime_posters = []
    count =0
    for i in distances[1:]:
        mal_id = animes.iloc[i[0]].MAL_ID
        url = fetch_poster(mal_id)
        if url == False:
            continue
        count+=1
        recommended_anime_posters.append(url)
        recommended_animes.append(animes.iloc[i[0]].Name)

        if count ==10:
            break
    
    return recommended_animes,recommended_anime_posters

st.header('Anime Recommendation System')
animes = pickle.load(open('./anime_list.pkl','rb'))
similarity = pickle.load(open('./similarity.pkl','rb'))

anime_list = animes['Name'].values
selected_anime = st.selectbox(
    "Type or select an anime from the dropdown",
    anime_list
)

if st.button('Show Recommendation'):
    recommended_animes,recommended_anime_posters = recommend(selected_anime)
    top_row_cols = st.columns(5)
    bottom_row_cols = st.columns(5)

    total_cards = min(10, len(recommended_animes), len(recommended_anime_posters))
    for idx in range(total_cards):
        target_col = top_row_cols[idx] if idx < 5 else bottom_row_cols[idx - 5]
        with target_col:
            st.text(recommended_animes[idx])
            st.image(recommended_anime_posters[idx])






    