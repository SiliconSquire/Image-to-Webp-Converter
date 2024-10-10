import os
import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QComboBox, QFileDialog, QProgressBar
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
from PIL import Image

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Image Converter")
        self.setGeometry(100, 100, 600, 400)
        icon_path = "icon.ico"  # Replace with the path to your icon file
        self.setWindowIcon(QIcon(icon_path))
        # Create central widget and layout
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Add widgets to the layout
        self.image_label = QLabel("Drag and drop images here", self)
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet("border: 2px dashed gray; padding: 20px;")
        layout.addWidget(self.image_label)
        
        options_layout = QHBoxLayout()
        
        self.size_combo = QComboBox(self)
        self.size_combo.addItems(["Original", "Small", "Medium", "Large"])
        options_layout.addWidget(QLabel("Size:", self))
        options_layout.addWidget(self.size_combo)
        
        self.quality_combo = QComboBox(self)
        self.quality_combo.addItems(["High", "Medium", "Low"])
        options_layout.addWidget(QLabel("Quality:", self))
        options_layout.addWidget(self.quality_combo)
        
        layout.addLayout(options_layout)
        
        buttons_layout = QHBoxLayout()
        
        self.select_button = QPushButton("Select Images", self)
        buttons_layout.addWidget(self.select_button)
        
        self.convert_button = QPushButton("Convert", self)
        buttons_layout.addWidget(self.convert_button)
        
        layout.addLayout(buttons_layout)
        
        self.progress_bar = QProgressBar(self)
        layout.addWidget(self.progress_bar)
        
        # Connect button clicks to functions
        self.select_button.clicked.connect(self.select_images)
        self.convert_button.clicked.connect(self.convert_images)
        
        # Initialize variables
        self.image_files = []
    
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
    
    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            event.setDropAction(Qt.DropAction.CopyAction)
            event.accept()
            
            # Clear previous image files
            self.image_files.clear()
            
            # Get dropped image files
            for url in event.mimeData().urls():
                file_path = url.toLocalFile()
                if file_path.lower().endswith(('.png', '.jpg', '.jpeg')):
                    self.image_files.append(file_path)
            
            # Update image label
            if self.image_files:
                self.image_label.setText(f"{len(self.image_files)} image(s) selected")
            else:
                self.image_label.setText("Drag and drop images here")
        else:
            event.ignore()
    
    def select_images(self):
        # Open file dialog to select images
        file_dialog = QFileDialog(self)
        file_dialog.setNameFilter("Images (*.png *.jpg *.jpeg)")
        file_dialog.setFileMode(QFileDialog.FileMode.ExistingFiles)
        
        if file_dialog.exec():
            self.image_files = file_dialog.selectedFiles()
            
            # Update image label
            if self.image_files:
                self.image_label.setText(f"{len(self.image_files)} image(s) selected")
            else:
                self.image_label.setText("Drag and drop images here")
    
    def convert_images(self):
        if not self.image_files:
            return
        
        # Get selected options
        size = self.size_combo.currentText()
        quality = self.quality_combo.currentText()
        
        # Set resize factor based on selected size
        resize_factor = 1.0
        if size == "Small":
            resize_factor = 0.5
        elif size == "Medium":
            resize_factor = 0.75
        elif size == "Large":
            resize_factor = 1.5
        
        # Set quality based on selected option
        quality_value = 100
        if quality == "Medium":
            quality_value = 75
        elif quality == "Low":
            quality_value = 50
        
        # Create output folder
        output_folder = "converted"
        os.makedirs(output_folder, exist_ok=True)
        
        # Convert images
        num_images = len(self.image_files)
        for i, image_file in enumerate(self.image_files):
            # Update progress bar
            progress = int((i + 1) / num_images * 100)  # Cast progress to integer
            self.progress_bar.setValue(progress)
            
            # Open image
            with Image.open(image_file) as img:
                # Resize image if needed
                if resize_factor != 1.0:
                    new_size = (int(img.width * resize_factor), int(img.height * resize_factor))
                    img = img.resize(new_size, Image.LANCZOS)
                
                # Save image as WebP
                output_file = os.path.join(output_folder, f"{os.path.splitext(os.path.basename(image_file))[0]}.webp")
                img.save(output_file, "WebP", quality=quality_value)
        
        # Reset progress bar
        self.progress_bar.setValue(0)
        
        # Show completion message
        self.image_label.setText(f"{num_images} image(s) converted successfully!")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())