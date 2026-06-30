import pickle
import streamlit as st
import requests

def fetch_poster(MAL_ID):
    jikan_url = "https://api.jikan.moe/v4/anime/{}".format(MAL_ID)
        
    try:
        response = requests.get(jikan_url, timeout=5)

        if response.status_code != 200:
            try:
                err = response.json()
            except ValueError:
                err = {}

            status = err.get("status", response.status_code)
            err_type = err.get("type", "HTTPError")
            message = err.get("message", "Unknown API error")
            return None, f"MAL_ID {MAL_ID} -> status={status}, type={err_type}, message={message}"

        data = response.json()
        poster_url = data["data"]["images"]["jpg"]["large_image_url"]
        return poster_url, None

    except requests.RequestException as e:
        return None, f"MAL_ID {MAL_ID} -> request error: {e}"
    except (KeyError, IndexError, TypeError, ValueError) as e:
        return None, f"MAL_ID {MAL_ID} -> parse error: {e}"
    

def recommend(anime):
    index = animes[animes['Name'] ==anime].index[0]
    distances = sorted(list(enumerate(similarity[index])),reverse=True, key = lambda x:x[1])
    recommended_animes = []
    recommended_anime_posters = []
    count =0
    continue_count =0
    shown_errors = set()
    for i in distances[1:]:
        if continue_count >= 20:
            break
        mal_id = animes.iloc[i[0]].MAL_ID
        url, err = fetch_poster(mal_id)

        if err and err not in shown_errors and len(shown_errors) < 3:
            st.warning(err)
            shown_errors.add(err)

        if not url:
            continue_count +=1
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
    tup = recommend(selected_anime)
    if not tup or not tup[0]:
        st.warning('Could not fetch enough posters right now. Please try again.')
        st.stop()
    recommended_animes,recommended_anime_posters = tup[0], tup[1]
    
    top_row_cols = st.columns(5)
    bottom_row_cols = st.columns(5)

    total_cards = min(10, len(recommended_animes), len(recommended_anime_posters))
    for idx in range(total_cards):
        target_col = top_row_cols[idx] if idx < 5 else bottom_row_cols[idx - 5]
        with target_col:
            st.text(recommended_animes[idx])
            st.image(recommended_anime_posters[idx])






