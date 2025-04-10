import os
import sys
import time

from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QComboBox,
    QFileDialog,
    QProgressBar,
    QMessageBox,
    QSlider,
    QLineEdit,
)
from PyQt6.QtCore import Qt, QObject, QThread, pyqtSignal
from PyQt6.QtGui import QIcon
from PIL import Image, UnidentifiedImageError


class ConversionWorker(QObject):
    """
    Worker object to perform image conversion in a separate thread.
    """

    progress = pyqtSignal(int)
    status_update = pyqtSignal(str)
    finished = pyqtSignal(int, int)
    error = pyqtSignal(str)

    def __init__(self, image_files, size_option, quality_value, output_folder):
        super().__init__()
        self.image_files = image_files
        self.size_option = size_option
        self.quality_value = quality_value
        self.output_folder = output_folder
        self._is_running = True

    def stop(self):
        self._is_running = False

    def run_conversion(self):
        if not self.image_files:
            self.error.emit("No images selected for conversion.")
            self.finished.emit(0, 0)
            return

        resize_factor = 1.0
        if self.size_option == "Small":
            resize_factor = 0.5
        elif self.size_option == "Medium":
            resize_factor = 0.75
        elif self.size_option == "Large":
            resize_factor = 1.5

        try:
            resample_filter = Image.Resampling.LANCZOS
        except AttributeError:
            resample_filter = Image.LANCZOS

        try:
            os.makedirs(self.output_folder, exist_ok=True)
        except OSError as e:
            self.error.emit(
                f"Could not create output folder '{self.output_folder}': {e}"
            )
            self.finished.emit(0, len(self.image_files))
            return

        num_images = len(self.image_files)
        success_count = 0
        fail_count = 0

        for i, image_file in enumerate(self.image_files):
            if not self._is_running:
                self.status_update.emit("Conversion cancelled.")
                break

            progress_percent = int((i / num_images) * 100)
            self.progress.emit(progress_percent)
            base_name = os.path.basename(image_file)
            self.status_update.emit(f"Processing ({i+1}/{num_images}): {base_name}")

            output_filename = f"{os.path.splitext(base_name)[0]}.webp"
            output_file = os.path.join(self.output_folder, output_filename)

            try:
                with Image.open(image_file) as img:
                    img_to_save = img
                    if img.mode in ("P", "L", "LA") and self.quality_value < 100:
                        img_to_save = img.convert("RGBA")
                    elif img.mode == "CMYK":
                        img_to_save = img.convert("RGB")
                    if resize_factor != 1.0:
                        new_size = (
                            int(img.width * resize_factor),
                            int(img.height * resize_factor),
                        )
                        new_size = (max(1, new_size[0]), max(1, new_size[1]))
                        img_to_save = img_to_save.resize(new_size, resample_filter)
                    lossless_mode = self.quality_value == 100
                    img_to_save.save(
                        output_file,
                        "WEBP",
                        quality=self.quality_value,
                        lossless=lossless_mode,
                    )

                success_count += 1

            except FileNotFoundError:
                self.status_update.emit(f"Error: File not found - {base_name}")
                fail_count += 1
            except PermissionError:
                self.status_update.emit(f"Error: Permission denied - {base_name}")
                fail_count += 1
            except UnidentifiedImageError:
                self.status_update.emit(f"Error: Cannot identify image - {base_name}")
                fail_count += 1
            except OSError as e:
                self.status_update.emit(f"Error processing {base_name}: {e}")
                fail_count += 1
            except Exception as e:
                self.status_update.emit(f"Unexpected error processing {base_name}: {e}")
                fail_count += 1

            QApplication.processEvents()

        if self._is_running:
            self.progress.emit(100)
        self.finished.emit(success_count, fail_count)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Image Converter")
        self.setGeometry(100, 100, 600, 400)
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.image_files = []
        self.output_folder = os.path.join(os.path.expanduser("~"), "converted_webp")
        self.conversion_thread = None
        self.conversion_worker = None
        icon_path = os.path.join(self.base_dir, "icon.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        else:
            print(f"Warning: Icon file not found at '{icon_path}'")

        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        self.image_label = QLabel(
            "Drag and drop images here or click 'Select Images'", self
        )
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setWordWrap(True)
        self.image_label.setStyleSheet(
            "border: 2px dashed gray; padding: 20px; min-height: 80px;"
        )
        layout.addWidget(self.image_label)

        self.setAcceptDrops(True)

        select_buttons_layout = QHBoxLayout()
        self.select_button = QPushButton("Select Images", self)
        select_buttons_layout.addWidget(self.select_button)

        self.clear_button = QPushButton("Clear Selection", self)
        select_buttons_layout.addWidget(self.clear_button)
        layout.addLayout(select_buttons_layout)

        output_layout = QHBoxLayout()
        self.select_output_button = QPushButton("Select Output Folder", self)
        output_layout.addWidget(self.select_output_button)

        self.output_path_display = QLineEdit(self)
        self.output_path_display.setText(os.path.abspath(self.output_folder))
        self.output_path_display.setReadOnly(True)
        output_layout.addWidget(self.output_path_display)
        layout.addLayout(output_layout)

        size_layout = QHBoxLayout()
        self.size_combo = QComboBox(self)
        self.size_combo.addItems(
            ["Original", "Small (50%)", "Medium (75%)", "Large (150%)"]
        )
        size_layout.addWidget(QLabel("Resize:", self))
        size_layout.addWidget(self.size_combo)
        layout.addLayout(size_layout)

        quality_layout = QHBoxLayout()
        self.quality_label = QLabel("Quality (20-100):", self)
        quality_layout.addWidget(self.quality_label)

        self.quality_slider = QSlider(Qt.Orientation.Horizontal, self)
        self.quality_slider.setMinimum(20)
        self.quality_slider.setMaximum(100)
        self.quality_slider.setValue(90)
        self.quality_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.quality_slider.setTickInterval(10)
        quality_layout.addWidget(self.quality_slider)

        self.quality_value_label = QLabel(f"{self.quality_slider.value()}%", self)
        self.quality_value_label.setMinimumWidth(40)
        quality_layout.addWidget(self.quality_value_label)
        layout.addLayout(quality_layout)

        self.convert_button = QPushButton("Convert to WebP", self)
        self.convert_button.setEnabled(False)
        layout.addWidget(self.convert_button)
        self.status_label = QLabel("Ready.", self)
        layout.addWidget(self.status_label)

        self.progress_bar = QProgressBar(self)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        layout.addWidget(self.progress_bar)

        self.select_button.clicked.connect(self.select_images)
        self.clear_button.clicked.connect(self.clear_selection)
        self.select_output_button.clicked.connect(self.select_output_directory)
        self.convert_button.clicked.connect(self.start_conversion)
        self.quality_slider.valueChanged.connect(self.update_quality_label)

        self.update_ui_after_selection()

    def dragEnterEvent(self, event):
        mime_data = event.mimeData()
        if mime_data.hasUrls() and all(url.isLocalFile() for url in mime_data.urls()):
            if any(
                url.toLocalFile()
                .lower()
                .endswith((".png", ".webp", ".jpg", ".jpeg", ".bmp", ".gif", ".tiff"))
                for url in mime_data.urls()
            ):
                event.acceptProposedAction()

    def dropEvent(self, event):
        valid_files = []
        for url in event.mimeData().urls():
            if url.isLocalFile():
                file_path = url.toLocalFile()
                if file_path.lower().endswith(
                    (".png", ".webp", ".jpg", ".jpeg", ".bmp", ".gif", ".tiff")
                ):
                    valid_files.append(file_path)

        if valid_files:
            self.image_files.extend(valid_files)
            self.image_files = sorted(list(set(self.image_files)))
            self.update_ui_after_selection()
        else:
            self.status_label.setText("Drop contained no supported image files.")
            event.ignore()

    def select_images(self):
        filter_string = (
            "Images (*.png *.jpg *.jpeg *.webp *.bmp *.gif *.tiff);;All Files (*)"
        )
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Images",
            "",
            filter_string,
        )
        if files:
            self.image_files.extend(files)
            self.image_files = sorted(list(set(self.image_files)))
            self.update_ui_after_selection()

    def clear_selection(self):
        """Clears the list of selected image files."""
        self.image_files.clear()
        self.update_ui_after_selection()
        self.status_label.setText("Selection cleared.")

    def select_output_directory(self):
        """Opens a dialog to select the output directory."""
        start_dir = self.output_folder if os.path.isdir(self.output_folder) else ""
        directory = QFileDialog.getExistingDirectory(
            self, "Select Output Folder", start_dir
        )
        if directory:
            self.output_folder = directory
            self.output_path_display.setText(self.output_folder)
            self.update_ui_after_selection()
            self.status_label.setText(f"Output folder set to: {self.output_folder}")

    def update_ui_after_selection(self):
        """Updates UI elements after files are selected, cleared, or output folder changes."""
        current_output_path = os.path.abspath(self.output_folder)
        self.output_path_display.setText(current_output_path)

        if self.image_files:
            self.image_label.setText(
                f"{len(self.image_files)} image(s) selected.\n"
                f"Ready to convert to WebP in '{current_output_path}' folder."
            )
            self.convert_button.setEnabled(True)
            self.status_label.setText(f"{len(self.image_files)} image(s) loaded.")
        else:
            self.image_label.setText(
                "Drag and drop images here or click 'Select Images'"
            )
            self.convert_button.setEnabled(False)
            if not hasattr(self, "status_label") or self.status_label.text() not in [
                "Selection cleared.",
                "Ready.",
            ]:
                pass
            else:
                self.status_label.setText("Ready.")
        self.progress_bar.setValue(0)

    def update_quality_label(self, value):
        """Updates the label next to the quality slider."""
        self.quality_value_label.setText(f"{value}%")

    def start_conversion(self):
        if not self.image_files:
            QMessageBox.warning(self, "No Images", "Please select images.")
            return

        if self.conversion_thread is not None and self.conversion_thread.isRunning():
            QMessageBox.information(self, "Busy", "Conversion in progress.")
            return

        try:
            os.makedirs(self.output_folder, exist_ok=True)
        except OSError as e:
            QMessageBox.critical(
                self,
                "Output Error",
                f"Cannot create output folder:\n{self.output_folder}\nError: {e}",
            )
            return

        size_map = {
            "Original": "Original",
            "Small (50%)": "Small",
            "Medium (75%)": "Medium",
            "Large (150%)": "Large",
        }
        size_option = size_map[self.size_combo.currentText()]
        quality_value = self.quality_slider.value()

        self.conversion_thread = QThread()
        self.conversion_worker = ConversionWorker(
            image_files=list(self.image_files),
            size_option=size_option,
            quality_value=quality_value,
            output_folder=self.output_folder,
        )
        self.conversion_worker.moveToThread(self.conversion_thread)

        self.conversion_worker.progress.connect(self.update_progress)
        self.conversion_worker.status_update.connect(self.update_status)
        self.conversion_worker.finished.connect(self.conversion_finished)
        self.conversion_worker.error.connect(self.conversion_error)

        self.conversion_thread.started.connect(self.conversion_worker.run_conversion)
        self.conversion_worker.finished.connect(self.conversion_thread.quit)
        self.conversion_worker.finished.connect(self.conversion_worker.deleteLater)
        self.conversion_thread.finished.connect(self.conversion_thread.deleteLater)

        self.set_controls_enabled(False)
        self.progress_bar.setValue(0)
        self.status_label.setText("Starting conversion...")

        self.conversion_thread.start()

    def set_controls_enabled(self, enabled):
        """Enable or disable UI controls during conversion."""
        self.select_button.setEnabled(enabled)
        self.clear_button.setEnabled(enabled)
        self.select_output_button.setEnabled(enabled)

        self.convert_button.setEnabled(enabled and bool(self.image_files))
        self.size_combo.setEnabled(enabled)
        self.quality_slider.setEnabled(enabled)
        self.setAcceptDrops(enabled)

    def update_progress(self, value):
        self.progress_bar.setValue(value)

    def update_status(self, message):
        self.status_label.setText(message)

    def conversion_error(self, message):
        QMessageBox.critical(self, "Conversion Error", message)
        self.status_label.setText(f"Error: {message}")
        self.set_controls_enabled(True)
        self.progress_bar.setValue(0)

    def conversion_finished(self, success_count, fail_count):

        final_output_path = os.path.abspath(self.output_folder)
        self.status_label.setText(
            f"Conversion complete: {success_count} succeeded, {fail_count} failed."
        )
        QMessageBox.information(
            self,
            "Conversion Complete",
            f"Finished converting images.\n"
            f"Success: {success_count}\n"
            f"Failed: {fail_count}\n\n"
            f"Output saved to '{final_output_path}'",
        )
        self.set_controls_enabled(True)
        self.conversion_thread = None
        self.conversion_worker = None

    def closeEvent(self, event):
        if self.conversion_thread is not None and self.conversion_thread.isRunning():
            reply = QMessageBox.question(
                self,
                "Confirm Exit",
                "Conversion in progress. Cancel and exit?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                if self.conversion_worker:
                    self.conversion_worker.stop()
                self.conversion_thread.quit()
                if not self.conversion_thread.wait(1000):
                    print("Warning: Thread termination timeout.")
                    self.conversion_thread.terminate()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
