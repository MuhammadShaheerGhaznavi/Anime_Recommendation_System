import pickle
import streamlit as st
import requests

@st.cache_data
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
    

@st.cache_data
def fetch_anime_details(mal_id): # full response of api.jikan.moe/v4/anime/{mal_id}/full
    url = f"https://api.jikan.moe/v4/anime/{mal_id}/full"
    r = requests.get(url, timeout=8)
    r.raise_for_status()
    return r.json().get("data", {})

@st.cache_data
def fetch_anime_gallery(mal_id):
    url = f"https://api.jikan.moe/v4/anime/{mal_id}/pictures"
    r = requests.get(url, timeout=8)
    r.raise_for_status()
    data = r.json().get("data", [])
    return [img.get("jpg", {}).get("large_image_url") for img in data if img.get("jpg", {}).get("large_image_url")]

def recommend(anime):
    index = animes[animes['Name'] ==anime].index[0]
    distances = sorted(list(enumerate(similarity[index])),reverse=True, key = lambda x:x[1])

    recs = []
    count =0
    continue_count =0
    shown_errors = set()
    for i in distances[1:]:
        if continue_count >= 20 or count ==10:
            break
        
        mal_id = animes.iloc[i[0]].MAL_ID
        name = animes.iloc[i[0]].Name
        url, err = fetch_poster(mal_id)

        if err and err not in shown_errors and len(shown_errors) < 3:
            st.warning(err)
            shown_errors.add(err)

        if not url:
            continue_count +=1
            continue

        count+=1
        recs.append({'name': name, 'poster': url, 'mal_id':mal_id})
  
    return recs

st.header('Anime Recommendation System')
animes = pickle.load(open('./anime_list.pkl','rb'))
similarity = pickle.load(open('./similarity.pkl','rb'))

anime_list = animes['Name'].values
selected_anime = st.selectbox(
    "Type or select an anime from the dropdown",
    anime_list
)

if "recs" not in st.session_state:
    st.session_state['recs'] = []

if 'dialog_open' not  in st.session_state:
    st.session_state['dialog_open'] = False

if "selected_rec" not in st.session_state:  # how would selected anime update after the intial assignment
    st.session_state["selected_rec"] = None
    

@st.dialog("Anime Details", width="large")
def show_dialog_contents():
    rec = st.session_state.get("selected_rec")
    
    if not rec:
        st.warning("No anime selected.")
        return

    mal_id = rec["mal_id"]

    try:
        with st.spinner("Loading details..."):
            details = fetch_anime_details(mal_id)
            gallery = fetch_anime_gallery(mal_id)
    except requests.RequestException as e:
        st.warning(f"Failed to fetch anime details: {e}")
        return

    title = details.get("title", rec["name"])
    synopsis = details.get("synopsis", "No synopsis available.")
    mal_url = details.get("url")
    trailer_url = (details.get("trailer") or {}).get("url")

    st.subheader(title)
    st.write(synopsis)

    if mal_url:
        st.link_button("Open MAL Page", mal_url)
    if trailer_url:  # my code usually doesnot return a trailre
        st.link_button("Watch Trailer", trailer_url)

    if gallery:
        st.markdown("### Gallery")
        st.image(gallery)

    if st.button("Close", key=f"close_dialog_{mal_id}"):
        st.session_state["dialog_open"] = False
        st.session_state["selected_rec"] = None
        st.rerun()


if st.button('Show Recommendation'):

    tup = recommend(selected_anime) 
    if not tup:
        st.warning('Could not fetch enough posters right now. Please try again.')
        st.stop()
    st.session_state["recs"] = tup
    st.session_state["dialog_open"] = False # when does dialog open become True??
    st.session_state["selected_rec"] = None

if st.session_state["recs"]:
    st.markdown(":red[Click on the anime name for more details]")

    top_row_cols = st.columns(5)
    bottom_row_cols = st.columns(5)

    total_cards = min(10, len(st.session_state["recs"]))
    for idx in range(total_cards):
        rec = st.session_state["recs"][idx]
        target_col = top_row_cols[idx] if idx < 5 else bottom_row_cols[idx - 5]

        with target_col:
            if st.button(rec["name"], key=f"open_dialog_{rec['mal_id']}_{idx}", type="tertiary"):
                st.session_state["selected_rec"] = rec
                st.session_state["dialog_open"] = True
                st.rerun()

            st.image(rec["poster"])

if st.session_state.get("dialog_open"):
    show_dialog_contents()





