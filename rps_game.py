import sys, cv2, mediapipe as mp
from PyQt6 import QtCore, QtGui, QtWidgets

# ─── Constants & Helpers ───────────────────────────────────────────────────────

FINGER_TIPS = [4, 8, 12, 16, 20]
FINGER_PIPS = [3, 6, 10, 14, 18]
ICON_SIZE   = 64
MAX_ROUNDS  = 8
COUNT_START = 3  # seconds per round

def count_fingers(hand_landmarks, w, h):
    pts = [(int(lm.x * w), int(lm.y * h)) for lm in hand_landmarks.landmark]
    cnt = 0
    # thumb
    if pts[FINGER_TIPS[0]][0] < pts[FINGER_PIPS[0]][0]:
        cnt += 1
    # other fingers
    for tip, pip in zip(FINGER_TIPS[1:], FINGER_PIPS[1:]):
        if pts[tip][1] < pts[pip][1]:
            cnt += 1
    return cnt

def classify_rps(cnt):
    if cnt == 0:   return "rock"
    if cnt == 2:   return "scissors"
    if cnt == 5:   return "paper"
    return "unknown"

def get_computer_move(user_move):
    if user_move == "rock":     return "paper"
    if user_move == "paper":    return "scissors"
    if user_move == "scissors": return "rock"
    return "unknown"

def decide_winner(user, comp):
    if user == comp:
        return "tie"
    wins = {("rock","scissors"),("paper","rock"),("scissors","paper")}
    return "user" if (user, comp) in wins else "computer"


# ─── Main Application ─────────────────────────────────────────────────────────

class RPSWindow(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Rock Paper Scissors")

        # ─ State
        self.rounds        = 0
        self.user_score    = 0
        self.comp_score    = 0
        self.ties          = 0
        self.game_active   = False
        self.paused        = False
        self.countdown_val = COUNT_START
        self.capture_round = False
        self.show_prompt = False

        # ─ Load Icons
        self.icons = {}
        for name in ("rock","paper","scissors","unknown"):
            pix = QtGui.QPixmap(f"icons/{name}.png")
            self.icons[name] = pix.scaled(
                ICON_SIZE, ICON_SIZE,
                QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                QtCore.Qt.TransformationMode.SmoothTransformation
            )

        # ─ Build Left & Right Round‑history Columns ───────────────────────────────
        self.comp_round_icons = []
        self.user_round_icons = []
        for _ in range(MAX_ROUNDS):
            c = QtWidgets.QLabel(); c.setFixedSize(ICON_SIZE,ICON_SIZE)
            c.setPixmap(self.icons["unknown"])
            self.comp_round_icons.append(c)
            u = QtWidgets.QLabel(); u.setFixedSize(ICON_SIZE,ICON_SIZE)
            u.setPixmap(self.icons["unknown"])
            self.user_round_icons.append(u)

        left_col = QtWidgets.QVBoxLayout()
        left_col.addWidget(QtWidgets.QLabel("Computer Rounds"))
        for lbl in self.comp_round_icons:
            left_col.addWidget(lbl)
        left_col.addStretch()

        right_col = QtWidgets.QVBoxLayout()
        right_col.addWidget(QtWidgets.QLabel("Your Rounds"))
        for lbl in self.user_round_icons:
            right_col.addWidget(lbl)
        right_col.addStretch()

        # ─ Build Middle Control & Video Panel ────────────────────────────────────
        # 1) Round label
        self.round_lbl = QtWidgets.QLabel(f"Round: 0/{MAX_ROUNDS}")
        font_r = self.round_lbl.font(); font_r.setPointSize(18)
        self.round_lbl.setFont(font_r)
        self.round_lbl.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        # 2) Countdown display
        self.countdown_lbl = QtWidgets.QLabel(str(self.countdown_val))
        self.countdown_lbl.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        font_c = self.countdown_lbl.font(); font_c.setPointSize(24)
        self.countdown_lbl.setFont(font_c)

        # 3) Video feed
        self.video_label = QtWidgets.QLabel()
        self.video_label.setFixedSize(640, 480)

        # 4) Boxed Score Panel
        score_box = QtWidgets.QGroupBox("Score")
        score_layout = QtWidgets.QHBoxLayout()
        self.you_score_lbl  = QtWidgets.QLabel(f"You: 0")
        self.comp_score_lbl = QtWidgets.QLabel(f"Comp: 0")
        self.tie_score_lbl  = QtWidgets.QLabel(f"Ties: 0")
        for lbl in (self.you_score_lbl, self.comp_score_lbl, self.tie_score_lbl):
            fnt = lbl.font(); fnt.setPointSize(16); lbl.setFont(fnt)
            score_layout.addWidget(lbl)
        score_box.setLayout(score_layout)

        # 5) Control buttons
        self.start_btn = QtWidgets.QPushButton("Start")
        self.pause_btn = QtWidgets.QPushButton("Pause")
        self.quiz_btn  = QtWidgets.QPushButton("Quiz")
        self.quit_btn  = QtWidgets.QPushButton("Quit")
        self.pause_btn.setEnabled(False)
        self.quiz_btn.setEnabled(False)

        btns = QtWidgets.QHBoxLayout()
        btns.addWidget(self.start_btn)
        btns.addWidget(self.pause_btn)
        btns.addWidget(self.quiz_btn)
        btns.addWidget(self.quit_btn)

        # Assemble middle column
        middle_col = QtWidgets.QVBoxLayout()
        middle_col.addWidget(self.round_lbl)
        middle_col.addWidget(self.countdown_lbl)
        middle_col.addWidget(self.video_label)
        middle_col.addWidget(score_box)
        middle_col.addLayout(btns)

        # ─ Combine into Main Layout ───────────────────────────────────────────────
        main_layout = QtWidgets.QHBoxLayout(self)
        main_layout.addLayout(left_col)
        main_layout.addLayout(middle_col)
        main_layout.addLayout(right_col)

        # ─ MediaPipe & OpenCV Setup ───────────────────────────────────────────────
        self.cap      = cv2.VideoCapture(0)
        self.mp_hands = mp.solutions.hands
        self.mp_draw  = mp.solutions.drawing_utils
        self.hands    = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.7
        )

        # ─ Timers ────────────────────────────────────────────────────────────────
        self.video_timer     = QtCore.QTimer(); self.video_timer.timeout.connect(self.update_frame);     self.video_timer.start(30)
        self.countdown_timer = QtCore.QTimer(); self.countdown_timer.timeout.connect(self.update_countdown)

        # ─ Signals ────────────────────────────────────────────────────────────────
        self.start_btn.clicked.connect(self.start_game)
        self.pause_btn.clicked.connect(self.toggle_pause)
        self.quiz_btn.clicked.connect(self.show_quiz)
        self.quit_btn.clicked.connect(self.close)

    # ─── Game Control Methods ───────────────────────────────────────────────────
    def start_game(self):
        # reset state & UI
        self.rounds = self.user_score = self.comp_score = self.ties = 0
        self.game_active = True
        self.paused      = False
        self.countdown_val = COUNT_START
        self.capture_round = False
        self.start_btn.setEnabled(False)
        self.pause_btn.setEnabled(True); self.pause_btn.setText("Pause")
        self.quiz_btn.setEnabled(True)
        for lbl in self.comp_round_icons + self.user_round_icons:
            lbl.setPixmap(self.icons["unknown"])
        self.update_labels()
        self.round_lbl.setText(f"Round: 0/{MAX_ROUNDS}")
        self.countdown_lbl.setText(str(self.countdown_val))
        self.countdown_timer.start(1000)

    def toggle_pause(self):
        if not self.game_active:
            return
        if self.paused:
            self.paused = False
            self.pause_btn.setText("Pause")
            self.countdown_timer.start(1000)
        else:
            self.paused = True
            self.pause_btn.setText("Resume")
            self.countdown_timer.stop()

    def show_quiz(self):
        QtWidgets.QMessageBox.information(
            self, "Game Quiz",
            f"Rounds: {self.rounds}/{MAX_ROUNDS}\n"
            f"You: {self.user_score}\n"
            f"Computer: {self.comp_score}\n"
            f"Ties: {self.ties}"
        )

    # ─── Timers’ Callbacks ────────────────────────────────────────────────────────
    def update_countdown(self):
        if not self.game_active or self.paused:
            return
        if self.countdown_val > 0:
            self.countdown_val -= 1
            self.countdown_lbl.setText(str(self.countdown_val))
        else:
            self.countdown_lbl.setText("GO!")
            self.capture_round = True
            self.countdown_timer.stop()

    def _start_next_round(self):
        # hide the prompt
        self.show_prompt = False

        # then exactly as before: restart countdown or end game
        if self.rounds >= MAX_ROUNDS:
            self.game_active   = False
            self.start_btn.setEnabled(True)
            self.pause_btn.setEnabled(False)
            self.countdown_lbl.setText("Done")
        else:
            self.countdown_val = COUNT_START
            self.countdown_lbl.setText(str(self.countdown_val))
            if not self.paused:
                self.countdown_timer.start(1000)

    def update_frame(self):
        # 1) Grab frame
        ret, frame = self.cap.read()
        if not ret:
            return

        # 2) Mirror and convert to RGB for MediaPipe
        frame = cv2.flip(frame, 1)
        rgb   = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.hands.process(rgb)

        # 3) Default moves
        user_move = comp_move = "unknown"

        # 4) If a hand is detected, draw landmarks and possibly capture the round
        if results.multi_hand_landmarks:
            hand = results.multi_hand_landmarks[0]
            self.mp_draw.draw_landmarks(frame, hand, self.mp_hands.HAND_CONNECTIONS)

            if self.capture_round:
                # a) Classify user gesture
                h, w, _   = frame.shape
                cnt       = count_fingers(hand, w, h)
                user_move = classify_rps(cnt)
                comp_move = get_computer_move(user_move)

                # b) Advance round counter
                self.rounds += 1
                idx = self.rounds - 1

                # c) Scoring
                if user_move in ("rock", "paper", "scissors"):
                    winner = decide_winner(user_move, comp_move)
                    if winner == "user":
                        self.user_score += 1
                    elif winner == "computer":
                        self.comp_score += 1
                    else:
                        self.ties += 1
                else:
                    # unknown ⇒ user auto‑win
                    self.user_score += 1
                    # show persistent prompt for 2s
                    self.show_prompt = True

                # d) Update history icons
                self.comp_round_icons[idx].setPixmap(self.icons[comp_move])
                self.user_round_icons[idx].setPixmap(self.icons[user_move])

                # e) End this capture, stop countdown, schedule next round
                self.capture_round = False
                self.countdown_timer.stop()
                QtCore.QTimer.singleShot(2000, self._start_next_round)

        # 5) Draw the “Not recognized” prompt if needed
        if self.show_prompt:
            cv2.putText(
                frame,
                ":( Not recognized, you win!",
                (30, 50),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 0, 255),
                2,
                cv2.LINE_AA
            )

        # 6) Refresh the score and round labels
        self.update_labels()

        # 7) Convert and display the frame in the middle block
        img = QtGui.QImage(
            frame.data,
            frame.shape[1],
            frame.shape[0],
            frame.strides[0],
            QtGui.QImage.Format.Format_BGR888
        )
        self.video_label.setPixmap(QtGui.QPixmap.fromImage(img))
    
    def update_labels(self):
        if self.game_active:
            disp_round = min(self.rounds + 1, MAX_ROUNDS)
        else:
            # Once the game ends, just show the total rounds played
            disp_round = self.rounds
        self.you_score_lbl.setText(f"You:  {self.user_score}")
        self.comp_score_lbl.setText(f"Comp: {self.comp_score}")
        self.tie_score_lbl.setText(f"Ties: {self.ties}")
        self.round_lbl.setText(f"Round: {disp_round}/{MAX_ROUNDS}")

    def closeEvent(self, event):
        self.video_timer.stop()
        self.countdown_timer.stop()
        self.cap.release()
        self.hands.close()
        event.accept()


# ─── Entry Point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    win = RPSWindow()
    win.show()
    sys.exit(app.exec())
