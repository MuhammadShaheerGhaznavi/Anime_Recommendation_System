# 🎌 Anime Recommendation System

A clean, responsive anime recommendation web app built with **Streamlit** and Python. It suggests new shows based on content similarity and lets users fine-tune their results using a custom filters menu. Users can click any recommended anime to open a detailed pop-up complete with a synopsis, MyAnimeList (MAL) score, official links, and an image gallery.

---

## ✨ Features

* **Instant Recommendations**: Pick an anime from the dropdown menu to immediately see highly relevant recommendations.
* **Custom Filters**: Adjust your results on the fly using a dedicated settings menu:
  * Control exactly how many recommendations to display.
  * Filter out low-rated shows by setting a minimum MAL score.
  * Hide same-franchise sequels so your results don't get flooded with multiple seasons of the same show.
* **Rich Details Pop-up**: Click any recommendation to view its full synopsis, score, official trailer link, and a gallery of images.

---

## Running the app (locally):

### Software Requirements:
Needs streamlit library to run the application

### Obtaining .pkl files:
Run `JupyterCode.ipynb` to get anime_list.pkl and similarity_pkl - containing the list of animes and the similarity scores
Then `script.py` to store the anime details and posters - this script takes several hours to run. Can alternatively just run `app_live_fetch.py` **
### Finally

run the following command in your terminal `streamlit run app.py` (use app_live_fetch.py **)

** it doesnot have all the features and is much slower than the newer `app.py`
---

## 🛠️ How It Works (Under the Hood)

### 1. Data Preparation:
Used the following Kaggle Dataset (https://www.kaggle.com/datasets/hernan4444/anime-recommendation-database-2020?) Which contains  ~ 17,000 animes scraped from MAL, uptil 2020. 
Then used JupyterCode.ipynb to clean the dataset and used it to create anime_list.pkl and similarity.pkl - containing the list of animes and the similarity scores of each anime with every other anime (using Bag of Words vectorization and cosine similarity)

### 2. Storing Anime Details:
Used scipt.py to iterate through the animes in anime_list.pkl and invoke jikan api requests to fetch that particular anime details and poster urls; I then stored this data into anime_details.pkl and anime_gallery.pkl respectively. This makes the web app much more responsive compared to live fetching the details from jikan api during runtime (which I was previous doing). 

### 3. Smart Caching
Loading dataframes and large similarity matrices from local disk on every button click slows things down. To keep the app fast and snappy, I used Streamlit's built-in decorators:
* `@st.cache_resource` handles loading the heavy model data (`anime_list.pkl`, `similarity.pkl`, etc) just once on startup.
* `@st.cache_data` caches the recommendation calculations so looking up the same anime twice is instantaneous.