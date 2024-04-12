import os
from flask import Flask, render_template, request, redirect, url_for
import cv2
import numpy as np
from ultralytics import YOLO
from ultralytics.utils.plotting import Annotator, colors
from collections import defaultdict
import time
import psycopg2
from ultralytics.solutions import speed_estimation

app = Flask(__name__)

# Connexion à la BDD
conn = psycopg2.connect(
    host="localhost",
    database="vehdetect",
    user="vehdetect",
    password="",
    port="5432"
)

track_history = defaultdict(lambda: [])
model = YOLO("models/yolov8n.pt")
names = model.model.names

# Définition des coordonnées de la zone d'intérêt (ROI) pour le comptage
roi = [(100, 200), (300, 400)]


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # Traitement du formulaire d'upload
        if 'video' not in request.files:
            return redirect(request.url)
        file = request.files['video']
        if file.filename == '':
            return redirect(request.url)
        if file:
            original_filename = file.filename
            video_path = os.path.join("uploads", original_filename)
            file.save(video_path)
            use_case = request.form.get('use_case')
            if use_case == 'tracking':
                return redirect(url_for('process_video', filename=original_filename))
            elif use_case == 'speed':
                return redirect(url_for('process_speed', filename=original_filename))
            # elif use_case == 'counting':
                # return redirect(url_for('process_counting', filename=original_filename))
    return render_template('index.html')


vehicle_count = 0
@app.route('/process/<filename>')
def process_video(filename):
    start_time = time.time()

    video_path = os.path.join("uploads", filename)  # Construction du chemin complet vers la vidéo uploadée

    cap = cv2.VideoCapture(video_path)
    assert cap.isOpened(), "Error reading video file"

    w, h, fps = (int(cap.get(x)) for x in (cv2.CAP_PROP_FRAME_WIDTH, cv2.CAP_PROP_FRAME_HEIGHT, cv2.CAP_PROP_FPS))

    result = cv2.VideoWriter("static/object_tracking.mp4",
                             cv2.VideoWriter_fourcc(*'avc1'),
                             fps,
                             (w, h))

    # Initialisation d'un ensemble pour suivre les identifiants des véhicules déjà comptés
    counted_vehicles = set()

    while cap.isOpened():
        success, frame = cap.read()
        if success:
            results = model.track(frame, persist=True, verbose=False)
            boxes = results[0].boxes.xyxy.cpu()

            if results[0].boxes.id is not None:
                # Extraction des résultats de la prédiction
                clss = results[0].boxes.cls.cpu().tolist()
                track_ids = results[0].boxes.id.int().cpu().tolist()
                confs = results[0].boxes.conf.float().cpu().tolist()

                # Initialisation de l'annotateur
                annotator = Annotator(frame, line_width=2)

                for box, cls, track_id in zip(boxes, clss, track_ids):
                    annotator.box_label(box, color=colors(int(cls), True), label=names[int(cls)])

                    # Sauvgarde historique tracking
                    track = track_history[track_id]
                    track.append((int((box[0] + box[2]) / 2), int((box[1] + box[3]) / 2)))
                    if len(track) > 30:
                        track.pop(0)

                    # Affichage tracking
                    points = np.array(track, dtype=np.int32).reshape((-1, 1, 2))
                    cv2.circle(frame, (track[-1]), 7, colors(int(cls), True), -1)
                    cv2.polylines(frame, [points], isClosed=False, color=colors(int(cls), True), thickness=2)

                    # Vérifier si les véhicules traversent la zone d'intérêt
                    center = ((box[0] + box[2]) / 2, (box[1] + box[3]) / 2)
                    if is_inside_roi(center, roi):
                        # Vérifier si le véhicule est déjà compté
                        if track_id not in counted_vehicles:
                            # Compter le véhicule et marquer comme compté
                            global vehicle_count
                            vehicle_count += 1
                            counted_vehicles.add(track_id)

            # Ecriture vidéo de sortie
            result.write(frame)

        else:
            break

    # Libération des ressources
    result.release()
    cap.release()
    cv2.destroyAllWindows()

    # Récupération de la durée de la vidéo
    data = cv2.VideoCapture(video_path)
    frames = data.get(cv2.CAP_PROP_FRAME_COUNT)
    fps = data.get(cv2.CAP_PROP_FPS)

    video_duration = round(frames / fps)

    video_name = filename
    video_size = os.path.getsize(video_path)

    # Insertion données dans la BDD
    cur = conn.cursor()

    cur.execute("SELECT version();")
    db_version = cur.fetchone()
    print("Version de la base de données :", db_version)

    try:
        cur.execute(
            "INSERT INTO video_information (video_name, video_duration, video_size, vehicle_count) VALUES (%s, %s, %s, %s)", (video_name, video_duration, video_size, vehicle_count))
        conn.commit()
    except psycopg2.Error as e:
        conn.rollback()
        print("Error inserting data into database:", e)
    # cur.close()
    # conn.close()

    print("Time execution : " + str((time.time() - start_time)) + " seconds")

    return render_template('result.html', vehicle_count=vehicle_count)

@app.route('/process_speed/<filename>')
def process_speed(filename):
    # Construction du chemin complet vers la vidéo uploadée
    video_path = os.path.join("uploads", filename)

    # Ouverture de la vidéo
    cap = cv2.VideoCapture(video_path)
    assert cap.isOpened(), "Error reading video file"
    w, h, fps = (int(cap.get(x)) for x in (cv2.CAP_PROP_FRAME_WIDTH, cv2.CAP_PROP_FRAME_HEIGHT, cv2.CAP_PROP_FPS))

    # Video writer
    video_writer = cv2.VideoWriter("static/speed_estimation.mp4",
                                   cv2.VideoWriter_fourcc(*'avc1'),
                                   fps,
                                   (w, h))

    # Définition des coordonnées de la ligne de référence pour le calcul de la vitesse
    line_pts = [(0, 360), (1280, 360)]

    # Initialisation de l'objet pour le calcul de la vitesse
    speed_obj = speed_estimation.SpeedEstimator()
    speed_obj.set_args(reg_pts=line_pts,
                       names=names,
                       view_img=True)

    # Boucle pour lire et traiter chaque frame de la vidéo
    while cap.isOpened():
        success, frame = cap.read()
        if not success:
            print("Video frame is empty or video processing has been successfully completed.")
            break

        # Détection des objets dans la frame
        results = model.track(frame, persist=True, verbose=False)
        boxes = results[0].boxes.xyxy.cpu()

        # Extraction des résultats de la prédiction
        clss = results[0].boxes.cls.cpu().tolist()
        track_ids = results[0].boxes.id.int().cpu().tolist()
        confs = results[0].boxes.conf.float().cpu().tolist()

        # Initialisation de l'annotateur
        annotator = Annotator(frame, line_width=2)

        # Boucle pour itérer sur chaque objet détecté
        for box, cls, track_id in zip(boxes, clss, track_ids):
            # Annotation de la boîte englobante et du nom de la classe
            annotator.box_label(box, color=colors(int(cls), True), label=names[int(cls)])

            # Calcul de la vitesse de l'objet
            speed = speed_obj.estimate_speed(frame, box)

            # Affichage de la vitesse de l'objet sur la frame
            cv2.putText(frame, f'{speed:.2f} mph', (int(box[0]), int(box[1]) - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, colors(int(cls), True), 2)

        # Ecriture de la frame traitée dans le fichier de sortie
        video_writer.write(frame)

    # Libération des ressources
    cap.release()
    video_writer.release()
    cv2.destroyAllWindows()

    # Récupération de la durée de la vidéo
    data = cv2.VideoCapture(video_path)
    frames = data.get(cv2.CAP_PROP_FRAME_COUNT)
    fps = data.get(cv2.CAP_PROP_FPS)

    video_duration = round(frames / fps)

    # Insertion des données dans la base de données
    cur = conn.cursor()

    cur.execute("SELECT version();")
    db_version = cur.fetchone()
    print("Version de la base de données :", db_version)

    try:
        cur.execute(
            "INSERT INTO video_information (video_name, video_duration, video_size, vehicle_count) VALUES (%s, %s, %s, %s)", (filename, video_duration, os.path.getsize(video_path), 0))
        conn.commit()
    except psycopg2.Error as e:
        conn.rollback()
        print("Error inserting data into database:", e)

    # Fermeture de la connexion à la base de données
    cur.close()
    conn.close()

    # Redirection vers la page de résultats
    return redirect(url_for('result'))

@app.route('/video_info')
def video_info():
    # Connexion à la base de données
    conn = psycopg2.connect(
        host="localhost",
        database="vehdetect",
        user="vehdetect",
        password="",
        port="5432"
    )

    # Récupération des données de la table video_information
    cur = conn.cursor()
    cur.execute("SELECT * FROM video_information")
    rows = cur.fetchall()
    cur.close()
    conn.close()

    # Passage des données au fichier HTML pour affichage
    return render_template('video_info.html', rows=rows)


# Fonction pour vérifier si un point se trouve à l'intérieur de la zone d'intérêt
def is_inside_roi(point, roi):
    x, y = point
    (x1, y1), (x2, y2) = roi
    return x1 <= x <= x2 and y1 <= y <= y2

if __name__ == '__main__':
    app.run(debug=True)
