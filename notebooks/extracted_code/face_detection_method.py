# Extracted face_detection method from monolithic app
# Original file: /Users/nickgklezakos/ppl-meta-alpha-staging/ppl-meta/face_detector.py

    def face_detection(self, media, logger, threshold=50):
        uid_generator = uuid.uuid4
        self.last_printed_progress = -1

        # Initialize the Dlib face detector
        detector = dlib.get_frontal_face_detector()

        settings_instance = settings.Settings()
        image_dir = settings_instance.image_dir
        face_pic_enlargement = settings_instance.face_pic_enlargement

        # Empty the 'face_pics' directory if it exists, otherwise create it
        if os.path.exists(image_dir):
            shutil.rmtree(image_dir)
        os.makedirs(image_dir)

        # Get the frames and total_frames from the media object
        frames, total_frames = media.get_data()

        # Dynamically construct the path to the 'models' directory
        base_dir = os.path.dirname(__file__)
        model_path = os.path.join(base_dir, 'models', 'haarcascade_frontalface_default.xml')

        # Load the Haar Cascade file using the absolute path
        face_cascade = cv2.CascadeClassifier(model_path)

        # Create the body cascade object
        #body_cascade = cv2.CascadeClassifier('ppl-meta/models/haarcascade_fullbody.xml')

        with Face(logger) as face:
            cursor = face.db_connection()
            cursor.execute("DROP TABLE IF EXISTS RawDetectionData")
            cursor.execute("DROP TABLE IF EXISTS FaceRects")
            cursor.execute("DROP TABLE IF EXISTS FacePics")
            cursor.execute("DROP TABLE IF EXISTS FaceUids")
            cursor.execute("DROP TABLE IF EXISTS MatchedFaces")
            cursor.execute("DROP TABLE IF EXISTS RawBodyDetectionData")
            cursor.execute("DROP TABLE IF EXISTS BodyRects")
            cursor.execute("DROP TABLE IF EXISTS BodyPics")
            cursor.execute("DROP TABLE IF EXISTS BodyUids")

            # Create new tables
            cursor.execute('''
                CREATE TABLE RawDetectionData (
                    Id INTEGER PRIMARY KEY,
                    frame BLOB,
                    timestamp REAL,
                    frame_path TEXT
                )
            ''')
            cursor.execute('''
                CREATE TABLE FaceRects (
                    Id INTEGER PRIMARY KEY,
                    RawDetectionDataId INTEGER,
                    rect_x INTEGER,
                    rect_y INTEGER,
                    rect_width INTEGER,
                    rect_height INTEGER,
                    grouptags REAL,
                    persontabs REAL,
                    FOREIGN KEY (RawDetectionDataId) REFERENCES RawDetectionData (Id)
                )
            ''')
            cursor.execute('''
                CREATE TABLE FacePics (
                    Id INTEGER PRIMARY KEY,
                    RawDetectionDataId INTEGER,
                    face_pic TEXT,
                    FaceDetectionFilter INTEGER,
                    age INTEGER,
                    gender TEXT,
                    FOREIGN KEY (RawDetectionDataId) REFERENCES RawDetectionData (Id)
                )
            ''')
            cursor.execute('''
                CREATE TABLE FaceUids (
                    Id INTEGER PRIMARY KEY,
                    RawDetectionDataId INTEGER,
                    face_uid TEXT,
                    age INTEGER,
                    FOREIGN KEY (RawDetectionDataId) REFERENCES RawDetectionData (Id)
                )
            ''')
            cursor.execute('''
                CREATE TABLE MatchedFaces (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    uid1 TEXT NOT NULL,
                    uid2 TEXT NOT NULL,
                    grouplabel TEXT
                )
            ''')

            # Create new tables for body detection data
            cursor.execute('''
                CREATE TABLE RawBodyDetectionData (
                    Id INTEGER PRIMARY KEY,
                    frame BLOB,
                    timestamp REAL,
                    frame_path TEXT
                )
            ''')
            cursor.execute('''
                CREATE TABLE BodyRects (
                    Id INTEGER PRIMARY KEY,
                    RawBodyDetectionDataId INTEGER,
                    rect_x INTEGER,
                    rect_y INTEGER,
                    rect_width INTEGER,
                    rect_height INTEGER,
                    grouptags REAL,
                    personstabs REAL,
                    FOREIGN KEY (RawBodyDetectionDataId) REFERENCES RawBodyDetectionData (Id)
                )
            ''')
            cursor.execute('''
                CREATE TABLE BodyPics (
                    Id INTEGER PRIMARY KEY,
                    RawBodyDetectionDataId INTEGER,
                    body_pic TEXT,
                    FOREIGN KEY (RawBodyDetectionDataId) REFERENCES RawBodyDetectionData (Id)
                )
            ''')
            cursor.execute('''
                CREATE TABLE BodyUids (
                    Id INTEGER PRIMARY KEY,
                    RawBodyDetectionDataId INTEGER,
                    body_uid TEXT,
                    FOREIGN KEY (RawBodyDetectionDataId) REFERENCES RawBodyDetectionData (Id)
                )
            ''')

            # First face detection with Open CV  **************************************************

            # Define frame detection rate
            frame_detection_rate = settings_instance.face_detection_rate

            # Calculate the interval for frame detection
            detection_interval = settings_instance.video_frame_rate // frame_detection_rate

            # Iterate over the frames
            for frame_number, frame_path in enumerate(frames):
                # Load the frame from the file
                frame = cv2.imread(frame_path)
                    
                # Get the current timestamp
                timestamp = time.time()

                # Frame processing
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

                # Perform face detection only on frames that match the interval
                if frame_number % detection_interval == 0:
                    # Use Haar cascade for face detection
                    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
                
                    face_pics = []
                    face_uids = []
                    face_rects = []

                    for (x, y, w, h) in faces:
                        # Calculate the additional face pic enlargement of width and height
                        w_increase = int(face_pic_enlargement * w)
                        h_increase = int(face_pic_enlargement * h)

                        # Adjust x, y, w, h to include the additional 20%
                        x_new = max(0, x - w_increase // 2)
                        y_new = max(0, y - h_increase // 2)
                        w_new = min(frame.shape[1] - x_new, w + w_increase)
                        h_new = min(frame.shape[0] - y_new, h + h_increase)

                        face_rect = (x_new, y_new, x_new + w_new, y_new + h_new)
                        face_rects.append(face_rect)

                        # Crop the face from the frame
                        face_pic = frame[y_new:y_new + h_new, x_new:x_new + w_new]

                        # Generate a unique ID for each face
                        uid = uid_generator()

                        # Save the face as an image file in the 'face_pics' directory
                        face_path = f'{image_dir}/face_{frame_number}_{x}_{y}.jpg'
                        cv2.imwrite(face_path, face_pic)
                        face_pics.append(face_path)
                        face_uids.append(uid)

                        # Add the face rectangle to face_rects
                        face_rects.append([x, y, w, h])

                        # Convert numpy.int64 values in face_rects to regular ints
                        #self.logger.debug(f'Before conversion, face_rects: {face_rects}')
                        face_rects = [[int(i) for i in inner] for inner in face_rects]
                        #self.logger.debug(f'After conversion, face_rects: {face_rects}')

                    # Second face detection with Dlib  **************************************************
                    
                    # Create new lists
                    filtered_face_pics = []
                    filtered_face_uids = []
                    filtered_face_rects = []

                    # Second loop to perform the second face detection with Dlib
                    for i, face_pic_path in enumerate(face_pics):
                        # Load the face picture
                        face_pic = cv2.imread(face_pic_path)

                        # Convert the face to grayscale
                        gray_face = cv2.cvtColor(face_pic, cv2.COLOR_BGR2GRAY)

                    # Perform face detection with Dlib **************************************************

                        dlib_faces = detector(gray_face, 1)

                        # If no faces are detected, then it's a false positive
                        if len(dlib_faces) == 0:
                            continue

                        # Add the items to the new lists
                        filtered_face_pics.append(face_pic_path)
                        filtered_face_uids.append(face_uids[i])
                        filtered_face_rects.append(face_rects[i])

                    # Replace the original lists with the filtered lists
                    face_pics = filtered_face_pics
                    face_uids = filtered_face_uids
                    face_rects = filtered_face_rects        
                    
                    # Only insert into the database if faces were detected
                    if face_pics:
                        for i in range(len(face_rects)):
                            # Convert the face rectangle and face image file path to JSON strings
                            face_rect_str = json.dumps([int(num) for num in face_rects[i]])
                            face_pic_str = json.dumps(face_pics[i])
                            face_uid_str = json.dumps([str(uid) for uid in face_uids])  # Convert each face ID to a string and then convert the list to a JSON string

                            # Insert the raw detection data into the RawDetectionData table
                            cursor.execute('''
                                INSERT INTO RawDetectionData (frame, frame_path, timestamp)
                                VALUES (?, ?, ?)
                            ''', (str(face_uids[i]), frame_path, timestamp))
                            raw_detection_data_id = cursor.lastrowid

                            # Insert the face rectangle into the FaceRects table
                            cursor.execute('''
                                INSERT INTO FaceRects (RawDetectionDataId, rect_x, rect_y, rect_width, rect_height)
                                VALUES (?, ?, ?, ?, ?)
                            ''', (raw_detection_data_id, face_rects[i][0], face_rects[i][1], face_rects[i][2] - face_rects[i][0], face_rects[i][3] - face_rects[i][1]))

                            # Insert the face image file path into the FacePics table
                            cursor.execute('''
                                INSERT INTO FacePics (RawDetectionDataId, face_pic)
                                VALUES (?, ?)
                            ''', (raw_detection_data_id, face_pics[i]))

                            # Insert the face ID into the FaceUids table
                            cursor.execute('''
                                INSERT INTO FaceUids (RawDetectionDataId, face_uid)
                                VALUES (?, ?)
                            ''', (raw_detection_data_id, str(face_uids[i])))

                        # After all the frames have been processed and data has been inserted into the tables
                        cursor.connection.commit()
                        # Log the number of updates made
                        logger.info(f"Number of face rects updates made: {len(face_rects)} from {total_frames} frames for {media} in face detection")

