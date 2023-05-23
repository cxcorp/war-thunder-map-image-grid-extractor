import cv2 as cv
from tesserocr import PyTessBaseAPI, PSM
from PIL import Image
import shutil
import os


# Directory paths
source_dir = "./images_source"

output_map_image_dir = "./output_maps"
output_fullcrop_image_dir = "./output_fullcrop"
output_grids_dir = "./output_grids"

# Create the output directory if it doesn't exist
os.makedirs(output_map_image_dir, exist_ok=True)
os.makedirs(output_fullcrop_image_dir, exist_ok=True)

if os.path.exists(output_grids_dir):
    shutil.rmtree(output_grids_dir)
os.makedirs(output_grids_dir, exist_ok=True)

# Get the list of image files in the source directory
image_files = [f for f in os.listdir(source_dir) if f.endswith((".png"))]

map_name_chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuüvwxyz123456789#-()[] "
grid_square_chars = "1234567890m "


def preprocessGridSquareImg(fullImg):
    # 333, 513 -> 539, 539
    imageRoi = fullImg[264:808, 875:1419]
    cropped = imageRoi[513:540, 333:540]
    b, g, r = cv.split(cropped)

    ret, thresholded = cv.threshold(g, 10, 255, cv.THRESH_BINARY)
    thresholded[23:, :] = 255
    return cv.cvtColor(thresholded, cv.COLOR_GRAY2BGR)


duplicateNames = dict()


def addDuplicateSuffixIfNecessary(name: str) -> str:
    currentCount = duplicateNames.get(name, 0)
    duplicateNames[name] = currentCount + 1

    return f"{name} ({currentCount})" if currentCount > 0 else name


# Process each image file
with PyTessBaseAPI(psm=PSM.SINGLE_LINE, lang="eng") as mapNameTesseract:
    with PyTessBaseAPI(psm=PSM.SINGLE_WORD, lang="eng") as gridSquareTesseract:
        mapNameTesseract.SetVariable("tessedit_char_whitelist", map_name_chars)
        gridSquareTesseract.SetVariable("tessedit_char_whitelist", grid_square_chars)

        for file_name in image_files:
            # Read the image
            image = cv.imread(os.path.join(source_dir, file_name))

            # crop from (876,210) to (1419, 264) and convert to RGB (cv2 imports as BGR)
            mapNameImg = cv.cvtColor(image[210:264, 876:1419], cv.COLOR_BGR2RGB)
            mapNameImgPil = Image.fromarray(mapNameImg)

            gridSquarePreprocessed = preprocessGridSquareImg(image)
            gridSquareImg = cv.cvtColor(gridSquarePreprocessed, cv.COLOR_BGR2RGB)

            gridSquareImgPil = Image.fromarray(gridSquareImg)

            mapNameTesseract.SetImage(mapNameImgPil)
            ocrMapName = addDuplicateSuffixIfNecessary(
                mapNameTesseract.GetUTF8Text().strip()
            )

            gridSquareTesseract.SetImage(gridSquareImgPil)
            ocrGridSquare = gridSquareTesseract.GetUTF8Text().strip()
            print(f'["{file_name}", "{ocrMapName}", "{ocrGridSquare}"],')

            cv.imwrite(
                os.path.join(output_grids_dir, ocrMapName + ".png"),
                gridSquarePreprocessed,
            )

            cv.imwrite(
                os.path.join(output_map_image_dir, ocrMapName + ".png"),
                # with white bezel: image[264:808, 875:1419]
                # without 6px white bezel:
                image[(264 + 6) : (808 - 6), (875 + 6) : (1419 - 6)],
            )

            # cv.imwrite(
            #     os.path.join(output_fullcrop_image_dir, ocrMapName + ".png"),
            #     image[210:808, 875:1419],
            # )

[
    print(f'Duplicate: "{key}": {value}')
    for key, value in duplicateNames.items()
    if value > 1
]
