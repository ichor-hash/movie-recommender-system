import pickle
import streamlit as st
import os
from dotenv import load_dotenv
from pathlib import Path
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from PIL import Image
import io
import time
import urllib3
import ssl
import certifi
import concurrent.futures
from functools import lru_cache
from streamlit.components.v1 import html
import json
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Load environment variables from project root
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

# Set page config must be the first Streamlit command
st.set_page_config(
    page_title="Movie Recommender System",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# TMDB API Configuration
TMDB_API_TOKEN = os.getenv('TMDB_API_TOKEN')
if not TMDB_API_TOKEN:
    st.error("""
    TMDB API token not found. Please create a .env file in the project root with:
    TMDB_API_TOKEN=your_token_here
    """)
    st.stop()

TMDB_BASE_URL = "https://api.themoviedb.org/3"
TMDB_IMAGE_BASE_URL = "https://image.tmdb.org/t/p/w500"

# Default poster URLs for fallback
DEFAULT_POSTER = "https://via.placeholder.com/500x750?text=No+Poster+Available"
DEFAULT_POSTER_ALT = "https://via.placeholder.com/500x750?text=Movie+Poster+Not+Found"

# Custom CSS
st.markdown("""
    <style>
    .stApp {
        background-color: #0E1117;
        color: #FFFFFF;
    }
    .movie-title {
        font-size: 1.2em;
        font-weight: bold;
        color: #FFFFFF;
        text-align: center;
        margin: 10px 0;
    }
    .movie-card {
        background-color: #1E2130;
        border-radius: 10px;
        padding: 10px;
        margin: 10px 0;
        transition: transform 0.3s;
    }
    .movie-card:hover {
        transform: scale(1.05);
    }
    .stButton>button {
        background-color: #FF4B4B;
        color: white;
        border-radius: 20px;
        padding: 10px 25px;
        font-weight: bold;
    }
    .stButton>button:hover {
        background-color: #FF6B6B;
    }
    
    /* Hamster Wheel Loader Styles */
    .wheel-and-hamster {
        --dur: 1s;
        position: relative;
        width: 12em;
        height: 12em;
        font-size: 14px;
    }

    .wheel,
    .hamster,
    .hamster div,
    .spoke {
        position: absolute;
    }

    .wheel,
    .spoke {
        border-radius: 50%;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
    }

    .wheel {
        background: radial-gradient(100% 100% at center,hsla(0,0%,60%,0) 47.8%,hsl(0,0%,60%) 48%);
        z-index: 2;
    }

    .hamster {
        animation: hamster var(--dur) ease-in-out infinite;
        top: 50%;
        left: calc(50% - 3.5em);
        width: 7em;
        height: 3.75em;
        transform: rotate(4deg) translate(-0.8em,1.85em);
        transform-origin: 50% 0;
        z-index: 1;
    }

    .hamster__head {
        animation: hamsterHead var(--dur) ease-in-out infinite;
        background: hsl(30,90%,55%);
        border-radius: 70% 30% 0 100% / 40% 25% 25% 60%;
        box-shadow: 0 -0.25em 0 hsl(30,90%,80%) inset,
                0.75em -1.55em 0 hsl(30,90%,90%) inset;
        top: 0;
        left: -2em;
        width: 2.75em;
        height: 2.5em;
        transform-origin: 100% 50%;
    }

    .hamster__ear {
        animation: hamsterEar var(--dur) ease-in-out infinite;
        background: hsl(0,90%,85%);
        border-radius: 50%;
        box-shadow: -0.25em 0 hsl(30,90%,55%) inset;
        top: -0.25em;
        right: -0.25em;
        width: 0.75em;
        height: 0.75em;
        transform-origin: 50% 75%;
    }

    .hamster__eye {
        animation: hamsterEye var(--dur) linear infinite;
        background-color: hsl(0,0%,0%);
        border-radius: 50%;
        top: 0.375em;
        left: 1.25em;
        width: 0.5em;
        height: 0.5em;
    }

    .hamster__nose {
        background: hsl(0,90%,75%);
        border-radius: 35% 65% 85% 15% / 70% 50% 50% 30%;
        top: 0.75em;
        left: 0;
        width: 0.2em;
        height: 0.25em;
    }

    .hamster__body {
        animation: hamsterBody var(--dur) ease-in-out infinite;
        background: hsl(30,90%,90%);
        border-radius: 50% 30% 50% 30% / 15% 60% 40% 40%;
        box-shadow: 0.1em 0.75em 0 hsl(30,90%,55%) inset,
                0.15em -0.5em 0 hsl(30,90%,80%) inset;
        top: 0.25em;
        left: 2em;
        width: 4.5em;
        height: 3em;
        transform-origin: 17% 50%;
        transform-style: preserve-3d;
    }

    .hamster__limb--fr,
    .hamster__limb--fl {
        clip-path: polygon(0 0,100% 0,70% 80%,60% 100%,0% 100%,40% 80%);
        top: 2em;
        left: 0.5em;
        width: 1em;
        height: 1.5em;
        transform-origin: 50% 0;
    }

    .hamster__limb--fr {
        animation: hamsterFRLimb var(--dur) linear infinite;
        background: linear-gradient(hsl(30,90%,80%) 80%,hsl(0,90%,75%) 80%);
        transform: rotate(15deg) translateZ(-1px);
    }

    .hamster__limb--fl {
        animation: hamsterFLLimb var(--dur) linear infinite;
        background: linear-gradient(hsl(30,90%,90%) 80%,hsl(0,90%,85%) 80%);
        transform: rotate(15deg);
    }

    .hamster__limb--br,
    .hamster__limb--bl {
        border-radius: 0.75em 0.75em 0 0;
        clip-path: polygon(0 0,100% 0,100% 30%,70% 90%,70% 100%,30% 100%,40% 90%,0% 30%);
        top: 1em;
        left: 2.8em;
        width: 1.5em;
        height: 2.5em;
        transform-origin: 50% 30%;
    }

    .hamster__limb--br {
        animation: hamsterBRLimb var(--dur) linear infinite;
        background: linear-gradient(hsl(30,90%,80%) 90%,hsl(0,90%,75%) 90%);
        transform: rotate(-25deg) translateZ(-1px);
    }

    .hamster__limb--bl {
        animation: hamsterBLLimb var(--dur) linear infinite;
        background: linear-gradient(hsl(30,90%,90%) 90%,hsl(0,90%,85%) 90%);
        transform: rotate(-25deg);
    }

    .hamster__tail {
        animation: hamsterTail var(--dur) linear infinite;
        background: hsl(0,90%,85%);
        border-radius: 0.25em 50% 50% 0.25em;
        box-shadow: 0 -0.2em 0 hsl(0,90%,75%) inset;
        top: 1.5em;
        right: -0.5em;
        width: 1em;
        height: 0.5em;
        transform: rotate(30deg) translateZ(-1px);
        transform-origin: 0.25em 0.25em;
    }

    .spoke {
        animation: spoke var(--dur) linear infinite;
        background: radial-gradient(100% 100% at center,hsl(0,0%,60%) 4.8%,hsla(0,0%,60%,0) 5%),
                linear-gradient(hsla(0,0%,55%,0) 46.9%,hsl(0,0%,65%) 47% 52.9%,hsla(0,0%,65%,0) 53%) 50% 50% / 99% 99% no-repeat;
    }

    @keyframes hamster {
        from, to {
            transform: rotate(4deg) translate(-0.8em,1.85em);
        }
        50% {
            transform: rotate(0) translate(-0.8em,1.85em);
        }
    }

    @keyframes hamsterHead {
        from, 25%, 50%, 75%, to {
            transform: rotate(0);
        }
        12.5%, 37.5%, 62.5%, 87.5% {
            transform: rotate(8deg);
        }
    }

    @keyframes hamsterEye {
        from, 90%, to {
            transform: scaleY(1);
        }
        95% {
            transform: scaleY(0);
        }
    }

    @keyframes hamsterEar {
        from, 25%, 50%, 75%, to {
            transform: rotate(0);
        }
        12.5%, 37.5%, 62.5%, 87.5% {
            transform: rotate(12deg);
        }
    }

    @keyframes hamsterBody {
        from, 25%, 50%, 75%, to {
            transform: rotate(0);
        }
        12.5%, 37.5%, 62.5%, 87.5% {
            transform: rotate(-2deg);
        }
    }

    @keyframes hamsterFRLimb {
        from, 25%, 50%, 75%, to {
            transform: rotate(50deg) translateZ(-1px);
        }
        12.5%, 37.5%, 62.5%, 87.5% {
            transform: rotate(-30deg) translateZ(-1px);
        }
    }

    @keyframes hamsterFLLimb {
        from, 25%, 50%, 75%, to {
            transform: rotate(-30deg);
        }
        12.5%, 37.5%, 62.5%, 87.5% {
            transform: rotate(50deg);
        }
    }

    @keyframes hamsterBRLimb {
        from, 25%, 50%, 75%, to {
            transform: rotate(-60deg) translateZ(-1px);
        }
        12.5%, 37.5%, 62.5%, 87.5% {
            transform: rotate(20deg) translateZ(-1px);
        }
    }

    @keyframes hamsterBLLimb {
        from, 25%, 50%, 75%, to {
            transform: rotate(20deg);
        }
        12.5%, 37.5%, 62.5%, 87.5% {
            transform: rotate(-60deg);
        }
    }

    @keyframes hamsterTail {
        from, 25%, 50%, 75%, to {
            transform: rotate(30deg) translateZ(-1px);
        }
        12.5%, 37.5%, 62.5%, 87.5% {
            transform: rotate(10deg) translateZ(-1px);
        }
    }

    @keyframes spoke {
        from {
            transform: rotate(0);
        }
        to {
            transform: rotate(-1turn);
        }
    }
    </style>
""", unsafe_allow_html=True)

def show_hamster_loader():
    """Display the hamster wheel loader component."""
    st.markdown("""
        <div style="display: flex; justify-content: center; align-items: center; margin: 20px 0;">
            <div aria-label="Orange and tan hamster running in a metal wheel" role="img" class="wheel-and-hamster">
                <div class="wheel"></div>
                <div class="hamster">
                    <div class="hamster__body">
                        <div class="hamster__head">
                            <div class="hamster__ear"></div>
                            <div class="hamster__eye"></div>
                            <div class="hamster__nose"></div>
                        </div>
                        <div class="hamster__limb hamster__limb--fr"></div>
                        <div class="hamster__limb hamster__limb--fl"></div>
                        <div class="hamster__limb hamster__limb--br"></div>
                        <div class="hamster__limb hamster__limb--bl"></div>
                        <div class="hamster__tail"></div>
                    </div>
                </div>
                <div class="spoke"></div>
            </div>
        </div>
    """, unsafe_allow_html=True)

# Create a session with retry mechanism
@st.cache_resource
def create_session():
    session = requests.Session()
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "HEAD"]
    )
    adapter = HTTPAdapter(
        max_retries=retry_strategy,
        pool_connections=10,
        pool_maxsize=10
    )
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session

# Cache for movie data
@st.cache_data(ttl=3600)
def get_movie_data(movie_id):
    session = create_session()
    try:
        url = f"{TMDB_BASE_URL}/movie/{movie_id}"
        headers = {
            'Authorization': f'Bearer {TMDB_API_TOKEN}',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        response = session.get(url, headers=headers, timeout=10, verify=False)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Error fetching movie data for ID {movie_id}: {str(e)}")
        return None
    finally:
        session.close()

def verify_image_url(url):
    session = create_session()
    try:
        response = session.head(url, timeout=10, verify=False)
        if response.status_code == 200:
            # Try to get the image to verify it's valid
            img_response = session.get(url, timeout=10, verify=False)
            if img_response.status_code == 200:
                # Try to open the image to verify it's valid
                Image.open(io.BytesIO(img_response.content))
                return True
        return False
    except Exception as e:
        logger.error(f"Error verifying image URL {url}: {str(e)}")
        return False
    finally:
        session.close()

def fetch_poster(movie_id):
    try:
        data = get_movie_data(movie_id)
        if not data or not data.get('poster_path'):
            return DEFAULT_POSTER
            
        full_path = f"{TMDB_IMAGE_BASE_URL}{data['poster_path']}"
        
        # Verify the image URL is accessible and valid
        if verify_image_url(full_path):
            return full_path
        else:
            # Try alternative poster size if available
            alt_path = f"https://image.tmdb.org/t/p/w342{data['poster_path']}"
            if verify_image_url(alt_path):
                return alt_path
            return DEFAULT_POSTER_ALT
            
    except Exception:
        return DEFAULT_POSTER

def fetch_posters_parallel(movie_ids):
    # Create a single container for all loading indicators in this function
    loading_container = st.empty()

    with loading_container.container():
        # Show the hamster loader
        show_hamster_loader()

        # Show loading status and progress bar
        st.markdown("### Loading movie posters...")
        progress_bar = st.progress(0)

    def update_progress(current, total):
        progress_bar.progress(current / total)

    results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        future_to_index = {
            executor.submit(fetch_poster, movie_id): idx
            for idx, movie_id in enumerate(movie_ids)
        }

        for i, future in enumerate(concurrent.futures.as_completed(future_to_index), 1):
            idx = future_to_index[future]
            result = future.result()
            if result:
                results[idx] = result
            update_progress(i, len(movie_ids))

    # Clear the entire loading container after processing
    loading_container.empty()

    return [results[i] for i in range(len(movie_ids))]

def recommend(movie):
    try:
        movie_indices = movies[movies['title'] == movie].index
        if len(movie_indices) == 0:
            st.error(f"Movie '{movie}' not found in the database")
            return [], []
            
        index = movie_indices[0]
        
        # Get similarity scores
        distances = sorted(list(enumerate(similarity[index])), reverse=True, key=lambda x: x[1])
        
        # Get top 5 recommendations
        recommended_movies = [(movies.iloc[i[0]].movie_id, movies.iloc[i[0]].title) for i in distances[1:6]]
        recommended_movie_ids = [movie_id for movie_id, _ in recommended_movies]
        recommended_movie_names = [title for _, title in recommended_movies]
        
        # Fetch posters in parallel - loading is handled within fetch_posters_parallel
        recommended_movie_posters = fetch_posters_parallel(recommended_movie_ids)
        
        return recommended_movie_names, recommended_movie_posters
        
    except Exception as e:
        st.error(f"An error occurred while getting recommendations: {str(e)}")
        return [], []

# Main content
st.title('🎬 Movie Recommender System')

# Sidebar
with st.sidebar:
    st.title("🎬 Movie Recommender")
    st.markdown("---")
    st.markdown("### About")
    st.markdown("""
    This app recommends movies based on your selection using content-based filtering and cosine similarity.
    Select a movie from the dropdown to get started!
    """)
    st.markdown("---")
    st.markdown("### How it works")
    st.markdown("""
    1. Select a movie you like
    2. Click 'Show Recommendations'
    3. Get 5 similar movie recommendations
    """)

# Load the model and data
@st.cache_data
def load_model_data():
    try:
        # Get the absolute path to the project root
        project_root = Path(__file__).parent.parent.absolute()
        
        # Load files from project root
        movies = pickle.load(open(project_root / 'movie_list.pkl', 'rb'))
        similarity = pickle.load(open(project_root / 'similarity.pkl', 'rb'))
        return movies, similarity
    except Exception as e:
        st.error(f"Error loading model files: {str(e)}")
        st.stop()

try:
    movies, similarity = load_model_data()
except Exception as e:
    st.error(f"Error loading model files: {str(e)}")
    st.stop()

# Movie selection with custom styling
st.markdown("### Select a Movie")
movie_list = movies['title'].values
selected_movie = st.selectbox(
    "Type or select a movie from the dropdown",
    movie_list,
    key="movie_selector"
)

# Show recommendations button
if st.button('Show Recommendations', key="recommend_button"):
    # The initial movie finding is fast, so we don't need a separate spinner here.
    # Loading for poster fetching is handled within fetch_posters_parallel.
    recommended_movie_names, recommended_movie_posters = recommend(selected_movie)

    # Display recommendations after fetching
    if recommended_movie_names and recommended_movie_posters:
        st.markdown("### Recommended Movies")
        cols = st.columns(5)
        for idx, (name, poster) in enumerate(zip(recommended_movie_names, recommended_movie_posters)):
            with cols[idx]:
                st.markdown(f'<div class="movie-card">', unsafe_allow_html=True)
                try:
                    st.image(poster, use_container_width=True)
                    st.markdown(f'<div class="movie-title">{name}</div>', unsafe_allow_html=True)
                except Exception as e:
                    st.error(f"Error displaying poster: {str(e)}")
                    st.image(DEFAULT_POSTER, use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center'>
    <p>Made with ❤️ using Streamlit and TMDB API by Adhiyaman Srinivasan</p>
</div>
""", unsafe_allow_html=True)





