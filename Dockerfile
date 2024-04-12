# Utiliser une image de base Python
FROM python:3.9

# Définir le répertoire de travail dans le conteneur
WORKDIR /app-vehdetect

# Copier les fichiers nécessaires dans le conteneur
COPY . .

# Installer les dépendances de l'application
RUN pip3 install -r requirements.txt

# Exposer le port sur lequel l'application Flask fonctionne
EXPOSE 5000

# Définir la commande à exécuter lorsque le conteneur démarre
CMD ["python", "server.py"]

# Construire l'image : docker build --tag app-vehdetect .
# Execution du conteneur : docker run -p 5000:5000 -d app-vehdetect