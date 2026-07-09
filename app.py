import pickle
import streamlit as st
import requests

st.header('Anime Recommendation System')

def unpickle(filename : str):
    dict ={}
    with open(filename, 'rb') as f:
        while True:
            try:
                dict.update(pickle.load(f))
            except EOFError:
                break
    return dict

@st.cache_resource
def global_resources():
    animes = pickle.load(open('./anime_list.pkl','rb'))
    similarity = pickle.load(open('./similarity.pkl','rb'))

    details = unpickle('anime_details.pkl')
    gallery = unpickle('anime_gallery.pkl')

    return animes, similarity, details, gallery

animes, similarity, details, gallery = global_resources()



def fetch_poster(MAL_ID):
    if details.get(f'{MAL_ID}', None):
        return details[f'{MAL_ID}']['images']['jpg']['large_image_url']
    return None
    


def fetch_anime_details(mal_id): 
    return details[f'{mal_id}'] 

def fetch_anime_gallery(mal_id):    
    return gallery[f'{mal_id}']

if "recs" not in st.session_state:
    st.session_state['recs'] = []

if 'dialog_open' not  in st.session_state:
    st.session_state['dialog_open'] = False

if "selected_rec" not in st.session_state:  # how would selected anime update after the intial assignment
    st.session_state["selected_rec"] = None

if 'selected_filters' not in st.session_state:
    st.session_state['selected_filters'] = {
        'num_recs' : 10,
        'lowest_rating': 6.5,
        'no_same_anime': False

    }

if 'filter_dialog_open' not in st.session_state:
    st.session_state['filter_dialog_open'] = False

@st.dialog("Filters", width="small", on_dismiss=lambda: st.session_state.update({"filter_dialog_open": False})) # type: ignore
def show_filter_options():
    filters = st.session_state['selected_filters']

    if not filters:
        st.warning('No Filter Selected')
        return

    num_recs = st.slider('Number of recommendations to show', 5, 50,filters.get('num_recs',10))
    lowest_rating = st.number_input('Lowest MAL Rating', min_value= 6.0, max_value=10.0, value=float(filters.get('lowest_rating',7.0)), step=0.1)
    no_same_anime = st.checkbox("Don't recommend same franchise", value=filters.get('no_same_anime', False) )

    if st.button('Apply & Close'):
        st.session_state['selected_filters'] = {
            'num_recs': num_recs,
            'lowest_rating': lowest_rating,
            'no_same_anime': no_same_anime
        }
        st.session_state['filter_dialog_open'] = False
        st.rerun()




@st.cache_data
def recommend(anime, selected_filters):
    index = animes[animes['Name'] ==anime].index[0]
    distances = sorted(list(enumerate(similarity[index])),reverse=True, key = lambda x:x[1])

    max_recs = selected_filters.get('num_recs',10)
    rating = selected_filters.get('lowest_rating', None)
    no_same = selected_filters.get('no_same_anime', False)

    recs = []
    count =0
    skip_count =0

    for i in distances[1:]:
        if count >= max_recs or skip_count >= 1000: 
            break
        
        mal_id = animes.iloc[i[0]].MAL_ID
        name = animes.iloc[i[0]].Name
        url = fetch_poster(mal_id)

        if not url:
            skip_count +=1
            continue
        if rating:
            anime_details = fetch_anime_details(mal_id)
            score = anime_details.get('score')
            if score is None or score < rating:
                continue
        if no_same:
            if name.lower() in anime.lower() or anime.lower() in name.lower():
                continue

        count+=1
        recs.append({'name': name, 'poster': url, 'mal_id':mal_id})
  
    return recs

anime_list = animes['Name'].values
selected_anime = st.selectbox(
    "Type or select an anime from the dropdown",
    anime_list
)



@st.dialog("Anime Details", width="large", on_dismiss=lambda: st.session_state.update({"dialog_open": False, "selected_rec": None}))  # type: ignore
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
    mal_score = details.get('score')
    ### need to parse trailer better
    trailer_url = (details.get("trailer") or {}).get("url") 

    st.subheader(title)
    st.write(synopsis)
    if mal_score:
        st.markdown(f'<u>MAL Score: {mal_score}</u>', unsafe_allow_html=True)

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

if st.session_state.get('filter_dialog_open'):
    st.session_state["dialog_open"] = False
    show_filter_options()
elif st.session_state.get("dialog_open"):
    st.session_state['filter_dialog_open'] = False
    show_dialog_contents()
 


col1, col2 = st.columns([4, 1])
with col1:
    if st.button('Show Recommendation', use_container_width=True):
        # Pass filters explicitly to your function here
        recs = recommend(selected_anime, st.session_state['selected_filters']) 
        if not recs:
            st.warning('Could not find recommendations matching these filters. Try lowering criteria.')
            st.stop()
        st.session_state["recs"] = recs
        st.session_state["dialog_open"] = False 
        st.session_state["selected_rec"] = None

with col2:
    if st.button('⚙️ Filters', use_container_width=True):
        st.session_state['filter_dialog_open'] = True
        st.rerun()

if st.session_state["recs"]:
    st.markdown(":red[Click on the anime name for more details]")

    recs_to_show = st.session_state["recs"]
    
    # Process recommendations dynamically in rows of 5
    for row_idx in range(0, len(recs_to_show), 5):
        row_chunk = recs_to_show[row_idx : row_idx + 5]
        cols = st.columns(5)
        
        for col_idx, rec in enumerate(row_chunk):
            global_idx = row_idx + col_idx
            with cols[col_idx]:
                if st.button(rec["name"], key=f"open_dialog_{rec['mal_id']}_{global_idx}", type="tertiary"):
                    st.session_state["selected_rec"] = rec
                    st.session_state["dialog_open"] = True
                    st.rerun()
                if rec['poster']:
                    st.image(rec["poster"])

# if st.session_state.get("dialog_open"):
#     show_dialog_contents()
