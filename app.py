import pickle
import streamlit as st
import requests

# pickle imports katao
# use fast api endpoints for data retrieval
API_BASE_URL = 'http://localhost:8000'
st.set_page_config(page_title='Anime Recommendation System', layout='wide')
st.header('Anime Recommendation System')

## API HELPERS
@st.cache_data(ttl=3600)
def get_anime_titles_map()-> dict[str, int]:
    try:
        response = requests.get(f'{API_BASE_URL}/animes', timeout=5)
        if response.status_code == 200: return response.json()
        st.error('Failed to load anime list from backend')
    except requests.RequestException as e:
        st.error(f'Cannot connect to API server. Error: {e}')
    return {}

def fetch_recommendations(mal_id: int, filters:dict)-> list[dict]:
    params = {
        'mal_id' : mal_id,
        'k': filters.get('num_recs', 10),
        'min_rating': filters.get('lowest_rating',0.0),
        'no_same': filters.get('no_same_anime', False)
    }
    try: 
        response = requests.get(f'{API_BASE_URL}/show_recommendations', params = params, timeout=10)
        if response.status_code ==200: return response.json()
        st.error('Backend error while fetching recommendations')
    except requests.RequestException as e:
        st.error(f'Cannot connect to API server. Error: {e}')
    return []

def fetch_anime_details(mal_id: int)->  dict|None:
    try:
        response = requests.get(f"{API_BASE_URL}/anime/{mal_id}", timeout=5)
        if response.status_code == 200:
            return response.json()
    except requests.RequestException as e:
        st.error(f"Error fetching anime details: {e}")
    return None


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


@st.dialog("Filters", width="small", on_dismiss=lambda: st.session_state.update({"filter_dialog_open": False})) 
def show_filter_options():
    filters = st.session_state['selected_filters']

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

@st.dialog("Anime Details", width="large", on_dismiss=lambda: st.session_state.update({"dialog_open": False, "selected_rec": None}))  # type: ignore
def show_dialog_contents():
    rec = st.session_state.get("selected_rec")
    
    if not rec:
        st.warning("No anime selected.")
        return
    mal_id = rec.get('mal') or rec.get('mal_id')
    if not mal_id:
        st.error("Invalid anime identifier.")
        return
    
    try:
        with st.spinner("Loading details..."):
            details = fetch_anime_details(mal_id)
    except requests.RequestException as e:
        st.error(f"Failed to load anime details: {e}")
        return

    # Check if details is None or not a dictionary
    if not details or not isinstance(details, dict):
        st.error("Failed to load anime details or invalid data returned.")
        return
        
    title = details.get("name", rec.get("name", "Unknown Title"))
    synopsis = details.get("desc", "No description available.")
    mal_url = details.get("mal_url")
    mal_score = details.get("score")
    gallery = details.get("gallery", []) 

    st.subheader(title)
    st.write(synopsis)
    if mal_score:
        st.markdown(f'<u>MAL Score: {mal_score}</u>', unsafe_allow_html=True)

    if mal_url:
        st.link_button(":red[Click to open MAL Page]", mal_url, type="tertiary")

    if gallery:
        st.markdown("### Gallery")
        st.image(gallery, width= 215)

    # if st.button("Close", key=f"close_dialog_{mal_id}"):
    #     st.session_state["dialog_open"] = False
    #     st.session_state["selected_rec"] = None
    #     st.rerun()

if st.session_state.get('filter_dialog_open'):
    st.session_state["dialog_open"] = False
    show_filter_options()
elif st.session_state.get("dialog_open"):
    st.session_state['filter_dialog_open'] = False
    show_dialog_contents()

## MAIN UI Controls
anime_map = get_anime_titles_map()
anime_names = list(anime_map.keys())

selected_anime_name = st.selectbox(
    'Type or select an anime from the dropdown',
    options=anime_names if anime_names else ['Loading...']
)

## Laying out the recommendations grid
col1, col2 = st.columns([4, 1])
with col1:
    if st.button("Show Recommendation", use_container_width=True):
        if selected_anime_name and selected_anime_name in anime_map:
            selected_mal_id = anime_map[selected_anime_name]
            
            with st.spinner("Fetching recommendations..."):
                recs = fetch_recommendations(selected_mal_id, st.session_state["selected_filters"])
            
            if not recs:
                st.warning("Could not find recommendations matching these filters. Try lowering criteria.")
                st.session_state["recs"] = []
            else:
                st.session_state["recs"] = recs
            
            st.session_state["dialog_open"] = False
            st.session_state["selected_rec"] = None

with col2:
    if st.button("⚙️ Filters", use_container_width=True):
        st.session_state["filter_dialog_open"] = True
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
                if st.button(rec["name"], key=f"open_dialog_{rec['mal']}_{global_idx}", type="tertiary"):
                    st.session_state["selected_rec"] = rec
                    st.session_state["dialog_open"] = True
                    st.rerun()
                if rec.get("img_url"):
                    st.image(rec["img_url"], use_container_width=True)
