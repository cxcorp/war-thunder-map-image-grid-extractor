import cv2 as cv
import numpy as np
import matplotlib.pyplot as plt
import shutil
import os
import pandas as pd
from scipy import signal

SOURCE_DIR = "./output_maps"
DEBUG_DIR = "./output_grid_pixel_debug"

if os.path.exists(DEBUG_DIR):
    shutil.rmtree(DEBUG_DIR)
os.makedirs(DEBUG_DIR, exist_ok=True)

# Get the list of image files in the source directory
imageFiles = [f for f in os.listdir(SOURCE_DIR) if f.endswith((".png"))]


def normalize(arr):
    return arr / np.max(arr)


clahe = cv.createCLAHE(clipLimit=5.0, tileGridSize=(8, 8))

kernelSize = 15
horizontalKernel = cv.getStructuringElement(cv.MORPH_RECT, (kernelSize, 1))
verticalKernel = cv.getStructuringElement(cv.MORPH_RECT, (1, kernelSize))

imageFileNameLens = [len(name) for name in imageFiles]
maxImageFileNameLen = np.max(imageFileNameLens)

allGridSizes = []

print("[")
for i, fileName in enumerate(imageFiles):
    image = cv.imread(os.path.join(SOURCE_DIR, fileName))

    mono = cv.cvtColor(image, cv.COLOR_BGR2LAB)
    # l, a, b = cv.split(mono)
    l = mono[:, :, 0]

    cl = clahe.apply(l)
    horizBlurred = cv.GaussianBlur(
        cl, (151, 1), sigmaX=5, sigmaY=1, borderType=cv.BORDER_WRAP
    )
    horizThreshd = cv.adaptiveThreshold(
        ~horizBlurred, 255, cv.ADAPTIVE_THRESH_MEAN_C, cv.THRESH_BINARY, 3, -2
    )

    vertBlurred = cv.GaussianBlur(
        cl, (1, 151), sigmaX=1, sigmaY=5, borderType=cv.BORDER_WRAP
    )
    vertThreshd = cv.adaptiveThreshold(
        ~vertBlurred, 255, cv.ADAPTIVE_THRESH_MEAN_C, cv.THRESH_BINARY, 3, -2
    )

    horizontal = cv.dilate(cv.erode(horizThreshd, horizontalKernel), horizontalKernel)
    vertical = cv.dilate(cv.erode(vertThreshd, verticalKernel), verticalKernel)

    vertical_sums = np.sum(vertical, axis=0)
    horizontal_sums = np.sum(horizontal, axis=1)
    # Reduce noise by adding the two sums together
    # Since the grid is perfectly horizontal and vertical and spaced
    # similarily in both directions, we can just add the two
    # to make the peaks stand out more in relation to noise on
    # either direction.
    both_sums_norm = normalize(vertical_sums + horizontal_sums)

    fig, ax = plt.subplots(13, 3)
    plt.subplots_adjust(hspace=0.4)

    ax[0, 1].imshow(cv.cvtColor(image, cv.COLOR_BGR2RGB))
    ax[0, 1].set_title("original")
    ax[0, 0].set_visible(False)
    ax[0, 2].set_visible(False)

    ax[1, 1].imshow(cv.cvtColor(l, cv.COLOR_GRAY2BGR))
    ax[1, 1].set_title("converted to LAB color, take only Luminance channel")
    ax[1, 0].set_visible(False)
    ax[1, 2].set_visible(False)

    ax[2, 0].imshow(cv.cvtColor(horizBlurred, cv.COLOR_GRAY2BGR))
    ax[2, 0].set_title("horizontal gaussian blur")
    ax[2, 2].imshow(cv.cvtColor(vertBlurred, cv.COLOR_GRAY2BGR))
    ax[2, 2].set_title("vertical gaussian blur")

    ax[3, 0].imshow(cv.cvtColor(horizThreshd, cv.COLOR_GRAY2BGR))
    ax[3, 0].set_title("adaptive thresholding")
    ax[3, 2].imshow(cv.cvtColor(vertThreshd, cv.COLOR_GRAY2BGR))
    ax[3, 2].set_title("adaptive thresholding")

    ax[4, 0].imshow(cv.cvtColor(horizontal, cv.COLOR_GRAY2BGR))
    ax[4, 0].set_title("horizontal erosion and dilation")
    ax[4, 2].imshow(cv.cvtColor(vertical, cv.COLOR_GRAY2BGR))
    ax[4, 2].set_title("vertical erosion and dilation")

    for x in range(0, 5):
        for y in range(0, 3):
            ax[x, y].axis("off")

    ax[5, 0].plot(horizontal_sums)
    ax[5, 0].set_title("row pixel values summed")
    ax[5, 2].plot(vertical_sums)
    ax[5, 2].set_title("column pixel values summed")
    ax[5, 1].set_visible(False)

    ax[6, 1].plot(vertical_sums + horizontal_sums)
    ax[6, 1].set_title("vertical_sums + horiz_sums")
    ax[6, 0].set_visible(False)
    ax[6, 2].set_visible(False)

    ax[7, 1].plot(both_sums_norm)
    ax[7, 1].set_title("normalize(vertical_sums + horiz_sums)")
    ax[7, 0].set_visible(False)
    ax[7, 2].set_visible(False)

    norm_copy = np.copy(both_sums_norm)
    norm_copy[norm_copy < 0.7] = 0
    ax[8, 1].plot(norm_copy)
    ax[8, 1].set_title("ignore all below 0.7")
    ax[8, 0].set_visible(False)
    ax[8, 2].set_visible(False)

    MIN_PEAK_DISTANCE_PX = 50
    peaks, _ = signal.find_peaks(
        both_sums_norm, height=0.7, distance=MIN_PEAK_DISTANCE_PX
    )
    ax[9, 1].plot(norm_copy)
    ax[9, 1].plot(peaks, both_sums_norm[peaks], "x")
    ax[9, 1].set_title("scipy.signal.find_peaks(distance=50)")
    ax[9, 0].set_visible(False)
    ax[9, 2].set_visible(False)

    peaksDf = pd.DataFrame(peaks, columns=["peaks_px"])
    # ax[10, 1].table(cellText=peaksDf.values, colLabels=peaksDf.columns, loc='center')
    # ax[10, 1].axis("off")
    # ax[10, 1].text(-0.35, 0, f"peaks_px={peaks}")
    # ax[10, 1].text(-0.4, -0.1, f"np.diff(peaks_px)={np.diff(peaks)}")
    ax[10, 1].plot(peaks, "o")
    ax[10, 1].set_title(f"peaks_px={peaks}")
    ax[10, 0].set_visible(False)
    ax[10, 2].set_visible(False)

    # ax[11, 1].table([[np.average(np.diff(peaks))]])
    ax[11, 1].plot(np.diff(peaks), "o")
    ax[11, 1].set_title(f"np.diff(peaks_px)={np.diff(peaks)}")
    ax[11, 0].set_visible(False)
    ax[11, 2].set_visible(False)

    ax[12, 1].plot([np.average(np.diff(peaks))], "o")
    ax[12, 1].set_title(f"np.average(np.diff(peaks))={np.average(np.diff(peaks))}")
    ax[12, 0].set_visible(False)
    ax[12, 2].set_visible(False)

    fig.set_size_inches(7, 30)
    fig.savefig(os.path.join(DEBUG_DIR, fileName))
    plt.close(fig)

    gridSizeInPixels = np.average(np.diff(peaks))
    print(
        f'["{fileName.replace(".png", "").ljust(maxImageFileNameLen + 1)}", {round(gridSizeInPixels, 2)}],'
    )
    allGridSizes.append([fileName, gridSizeInPixels])
print("]")

df = pd.DataFrame(allGridSizes, columns=["mapName", "gridSize"])
sortedDf = df.sort_values("gridSize")
print(df.describe())
print("")
print("Top 10: ")
print(sortedDf.head(10))
print("Bottom 10: ")
print(sortedDf.tail(10))
