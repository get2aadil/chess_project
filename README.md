# ChessMaster

ChessMaster is a real-time multiplayer chess platform built using Django and WebSockets. It allows users to play chess games online, track their game history, and manage their profiles. The application is designed to provide a seamless and interactive experience for chess enthusiasts.

## Features

- **User Authentication**: Supports user registration, login, and logout functionalities.
- **Guest Access**: Non-logged-in users can access the History, Rules, and About pages.
- **Game Restrictions**: Users cannot start a new game until their current game is completed.
- **Real-time Gameplay**: Utilizes WebSockets for real-time updates during gameplay.
- **Chessboard Rendering**: Displays a dynamic chessboard with move validation using UCI format.
- **Game History**: Allows users to view and manage their past games, including editing and deleting entries.
- **Journal Entries**: Users can create journal entries for each game to reflect on their strategies.

## Pages

- **Home**: Introduction to ChessMaster and its features.
- **About**: Information about the developer and the project.
- **Rules**: Detailed explanation of chess rules and gameplay.
- **History**: Overview of chess history and user's past games.

## Deployment

- **Docker**: The application is containerized using Docker for consistent deployment.
- **Google Cloud Platform (GCP)**: Deployed on GCP with a registered domain, HTTPS setup, and a load balancer capable of handling 1,000 requests per second using GCP-managed instances.
- **Redis and Daphne**: Redis is used for channel layers, and Daphne serves as the ASGI server for handling WebSocket connections.

## Technical Stack

- **Backend**: Django 5.1.1, Channels 4.1.0, python-chess 1.11.0
- **Frontend**: HTML, CSS, JavaScript, Bootstrap 4
- **Database**: PostgreSQL
- **Real-time Communication**: WebSockets via Django Channels

## Installation and Setup

1. **Clone the Repository**: 
   ```bash
   git clone <repository-url>
   ```

2. **Build Docker Image**: 
   ```bash
   docker build -t chessmaster .
   ```

3. **Run Docker Container**: 
   ```bash
   docker run -p 8000:8000 chessmaster
   ```

4. **Access the Application**: Visit `http://localhost:8000` in your browser.
