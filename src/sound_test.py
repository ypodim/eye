import pygame
import threading
import time

class Sounds:
    def __init__(self):
        self.running = 1
        pygame.init()
        pygame.mixer.init()

    def run(self):
        while self.running:

            print("ok")
            if pygame.mixer.music.get_busy(): 
                pygame.time.Clock().tick(10)
            else:
                self.play()
                time.sleep(0.1)
    def stop(self):
        self.running = 0 
        

    def play(self):
        file = 'files/birds-19624.mp3'
        
        pygame.mixer.music.load(file)
        pygame.mixer.music.play()


if __name__=="__main__":
    sound = Sounds()
    threading.Thread(target=sound.run).start()
    try:
        while 1:
            time.sleep(1)
    except KeyboardInterrupt:
        sound.stop()

