cmake_minimum_required(VERSION 3.13.4)

project(PcatMeasureExtension)

set(EXTENSION_HOMEPAGE "https://github.com/hattori222yu/SlicerPcatMeasure")
set(EXTENSION_CATEGORY "Quantification")
set(EXTENSION_CONTRIBUTORS "Masayuki Hattori (Yamagata University),Daisuke Kinoshita (Yamagata University)")
set(EXTENSION_DESCRIPTION "Pericoronary Adipose Tissue (PCAT) measurement and coronary centerline-based cross-sectional analysis for research use.")
set(EXTENSION_ICONURL "https://raw.githubusercontent.com/hattori222yu/SlicerPcatMeasure/Docs/icon.png")
set(EXTENSION_SCREENSHOTURLS "https://raw.githubusercontent.com/hattori222yu/SlicerPcatMeasure/Docs/PcatMeasure_colormap.png")
set(EXTENSION_DEPENDS "NA") # Specified as a list or "NA" if no dependencies

find_package(Slicer REQUIRED)
include(${Slicer_USE_FILE})

add_subdirectory(PcatMeasure)
add_subdirectory(CoronaryCenterlineCrossSection)