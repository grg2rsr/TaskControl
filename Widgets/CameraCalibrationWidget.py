import sys
import os
from pathlib import Path

sys.path.append("..")

from PyQt5 import QtCore
from PyQt5 import QtWidgets

import numpy as np
import cv2
import PySpin


class CameraCalibrationWidget(QtWidgets.QWidget):
    def __init__(self, parent, config, task_config):
        super(CameraCalibrationWidget, self).__init__(parent=parent)
        self.name = "CameraCalibrationWidget"

        # the original folder of the task
        self.task_folder = (
            Path(config["paths"]["tasks_folder"]) / config["current"]["task"]
        )
        self.config = config
        self.task_config = task_config

        self.initUI()

    def initUI(self):
        # the formlayout
        self.setWindowFlags(QtCore.Qt.Window)
        Layout = QtWidgets.QVBoxLayout(self)

        GridPositionBtn = QtWidgets.QPushButton()
        GridPositionBtn.setText("Show video with grid")
        GridPositionBtn.clicked.connect(self.GridPositionBtnClicked)
        Layout.addWidget(GridPositionBtn)

        CaptureBckgBtn = QtWidgets.QPushButton()
        CaptureBckgBtn.setText("capture reference images")
        CaptureBckgBtn.clicked.connect(self.CaptureBckgBtnClicked)
        Layout.addWidget(CaptureBckgBtn)

        SpoutAlignBtn = QtWidgets.QPushButton()
        SpoutAlignBtn.setText("Show background subtracted video")
        SpoutAlignBtn.clicked.connect(self.SpoutAlignBtnBtnClicked)
        Layout.addWidget(SpoutAlignBtn)

        self.setLayout(Layout)
        self.setWindowTitle("Camera Calibration")

        # settings
        self.settings = QtCore.QSettings("TaskControl", "CameraCalib")
        self.resize(self.settings.value("size", QtCore.QSize(270, 225)))
        self.move(self.settings.value("pos", QtCore.QPoint(10, 10)))
        self.show()

    def GridPositionBtnClicked(self):
        self.display_video_with_grid(verbose=False)
        pass

    def get_save_path(self):
        Animal = self.parent().Animal
        calib_folder = Path(self.config["paths"]["animals_folder"]).parent / "calib"
        save_path = calib_folder / "camera_calib_files" / Animal.ID
        return save_path

    def CaptureBckgBtnClicked(self):
        save_path = self.get_save_path()
        os.makedirs(save_path, exist_ok=True)
        n_frames = int(self.task_config["n_frames_for_bckg"])
        self.capture_ref_images(nFrames=n_frames, save=save_path, verbose=True)

    def SpoutAlignBtnBtnClicked(self):
        save_path = self.get_save_path()
        n_frames = int(self.task_config["n_frames_for_bckg"])
        fnames = [save_path / ("Acquisition-%i.jpg" % n) for n in range(n_frames)]
        Frames = [cv2.imread(str(fname))[:, :, 0] for fname in fnames]
        ref_img = np.average(np.array(Frames), axis=0)[:, :, np.newaxis]
        self.display_ref_subtracted_video(ref_img)

    def display_ref_subtracted_video(self, ref_img, verbose=False):
        # normalize
        ref_img = cv2.normalize(ref_img.astype("uint8"), None, 0, 255, cv2.NORM_MINMAX)[
            :, :, np.newaxis
        ]

        index = 0
        system = PySpin.System.GetInstance()
        cam_list = system.GetCameras()
        num_cameras = cam_list.GetSize()
        camera = cam_list.GetByIndex(index)

        camera.Init()
        camera.AcquisitionMode.SetValue(PySpin.AcquisitionMode_Continuous)
        height = camera.Height()
        width = camera.Width()
        channels = 1
        camera.BeginAcquisition()

        i = 0
        while True:
            i += 1
            image_result = camera.GetNextImage(1000)
            if image_result.IsIncomplete():
                print(
                    "Image incomplete with image status %d ..."
                    % image_result.GetImageStatus()
                )
            else:
                width = image_result.GetWidth()
                height = image_result.GetHeight()
                if verbose:
                    print(
                        "Grabbed Image %d, width = %d, height = %d" % (i, width, height)
                    )
                image_converted = image_result.Convert(
                    PySpin.PixelFormat_Mono8, PySpin.HQ_LINEAR
                )
                image_result.Release()

                frame = image_converted.GetData().reshape(height, width, channels)

                cv2.imshow("Frame", frame - ref_img)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    # cv2.destroyWindow('Frame')
                    break

        cv2.destroyAllWindows()
        camera.EndAcquisition()
        camera.DeInit()
        return None

    def display_video_with_grid(self, verbose=False):
        index = 0
        system = PySpin.System.GetInstance()
        cam_list = system.GetCameras()
        num_cameras = cam_list.GetSize()
        camera = cam_list.GetByIndex(index)

        camera.Init()
        camera.AcquisitionMode.SetValue(PySpin.AcquisitionMode_Continuous)
        height = camera.Height()
        width = camera.Width()
        channels = 1
        camera.BeginAcquisition()

        i = 0
        while True:
            i += 1
            image_result = camera.GetNextImage(1000)
            if image_result.IsIncomplete():
                print(
                    "Image incomplete with image status %d ..."
                    % image_result.GetImageStatus()
                )
            else:
                width = image_result.GetWidth()
                height = image_result.GetHeight()
                if verbose:
                    print(
                        "Grabbed Image %d, width = %d, height = %d" % (i, width, height)
                    )
                image_converted = image_result.Convert(
                    PySpin.PixelFormat_Mono8, PySpin.HQ_LINEAR
                )
                image_result.Release()

                frame = image_converted.GetData().reshape(height, width, channels)

                # crosshair
                cv2.line(
                    frame,
                    (0, int(height / 2)),
                    (width, int(height / 2)),
                    (255, 0, 0),
                    1,
                )
                cv2.line(
                    frame, (int(width / 2), 0), (int(width / 2), height), (255, 0, 0), 1
                )

                # spacers
                d = 10  # px
                n = 15  # spacers
                for j in range(n):
                    if j % 2 == 0:
                        v = 150
                    else:
                        v = 100
                    cv2.line(
                        frame,
                        (int(width / 2) + j * d, 0),
                        (int(width / 2) + j * d, height),
                        (v, 0, 0),
                        1,
                    )

                cv2.line(
                    frame, (int(width / 4), 0), (int(width / 4), height), (v, 0, 0), 1
                )
                cv2.line(
                    frame, (int(width / 5), 0), (int(width / 5), height), (v, 0, 0), 1
                )

                # diagonals - 45 deg
                min_dim = min(width, height)
                # cv2.line(frame,(int(width/2),int(height/2)), (int(width/2 + min_dim/2) , 0),(255,0,0),1)
                # cv2.line(frame,(int(width/2),int(height/2)), (int(width/2 + min_dim/2) , height),(255,0,0),1)

                # trigon def
                phi = 60
                phip = phi / 2 * 2 * np.pi / 360
                q = height * np.sin(phip)

                cv2.line(
                    frame,
                    (int(width / 2), int(height / 2)),
                    (int(width), int(height / 2 + q)),
                    (255, 0, 0),
                    1,
                )
                cv2.line(
                    frame,
                    (int(width / 2), int(height / 2)),
                    (int(width), int(height / 2 - q)),
                    (255, 0, 0),
                    1,
                )

                cv2.imshow("Frame", frame)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    # cv2.destroyWindow('Frame')
                    break

        cv2.destroyAllWindows()
        camera.EndAcquisition()
        camera.DeInit()
        return None

    def capture_ref_images(self, nFrames=100, save=None, verbose=False):
        index = 0
        system = PySpin.System.GetInstance()
        cam_list = system.GetCameras()
        num_cameras = cam_list.GetSize()
        camera = cam_list.GetByIndex(index)

        camera.Init()
        camera.AcquisitionMode.SetValue(PySpin.AcquisitionMode_Continuous)
        height = camera.Height()
        width = camera.Width()
        channels = 1

        camera.BeginAcquisition()

        i = 0

        frames = []

        for i in range(nFrames):
            image_result = camera.GetNextImage(1000)

            if image_result.IsIncomplete():
                print(
                    "Image incomplete with image status %d ..."
                    % image_result.GetImageStatus()
                )
            else:
                width = image_result.GetWidth()
                height = image_result.GetHeight()
                print("Grabbed Image %d, width = %d, height = %d" % (i, width, height))
                image_converted = image_result.Convert(
                    PySpin.PixelFormat_Mono8, PySpin.HQ_LINEAR
                )
                image_result.Release()

                frame = image_converted.GetData().reshape(height, width, channels)
                frames.append(frame)
                # cv2.imshow('Frame', frame)
                # if cv2.waitKey(1) & 0xFF == ord('q'):
                #     break

                if save is not None:
                    fname = save / ("Acquisition-%d.jpg" % i)
                    image_converted.Save(str(fname))
                    print("Image saved at %s" % fname)

        # cv2.destroyAllWindows()
        camera.EndAcquisition()
        camera.DeInit()
        return None

    def closeEvent(self, event):
        """reimplementation of closeEvent"""
        # Write window size and position to config file
        self.settings.setValue("size", self.size())
        self.settings.setValue("pos", self.pos())
