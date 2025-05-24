# Map Chat Application

A web application featuring a chat UI on the left side, a search box on the top right, and an interactive map background powered by deck.gl.

## Features

- Interactive map interface using deck.gl with MapLibre GL (free and open-source)
- Chat interface on the left side panel
- Location search functionality using Neo4j database
- Responsive design

## Technology Stack

- Frontend: React.js
- Map Visualization: deck.gl with MapLibre GL
- Database: Neo4j for location data
- Backend: FastAPI (optional)

## Getting Started

1. Clone the repository
2. Install dependencies: `npm install`
3. Create a `.env` file in the root directory with your Mapbox API key:
   ```
   REACT_APP_MAPBOX_TOKEN=your_mapbox_token_here
   ```
4. Start the development server: `npm start`

## Backend Setup (Optional)

If using the FastAPI backend for Neo4j integration:

1. Navigate to the `backend` directory
2. Install requirements: `pip install -r requirements.txt`
3. Configure Neo4j connection in `config.py`
4. Start the FastAPI server: `uvicorn main:app --reload` 