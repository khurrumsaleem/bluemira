set -e

NJOBS=$(nproc --ignore=2)
FORCE="false"

while getopts j:f option
do
  case "${option}"
  in
    j) NJOBS=${OPTARG};;
    f) FORCE="true"
  esac
done

if [[ $(basename $PWD) == *"bluemira"* ]]; then
  cd ..
fi

if [ -d freecad-build ]; then
  if ${FORCE}; then
    echo "Removing previous FreeCAD build."
    rm -rf freecad-build
  else
    echo "Existing freecad build exists. Use the flag -f if you want to rebuild."
    exit 1
  fi
fi

PYTHON_VERSION=`python -c 'import sys; version=sys.version_info[:2]; print("{0}.{1}".format(*version))'`
PYTHON_BIN=$(which python)
PYTHON_BIN_DIR=$(dirname $PYTHON_BIN)
PYTHON_PACKAGES_DIR=$(readlink --canonicalize $PYTHON_BIN_DIR/../lib/python$PYTHON_VERSION/site-packages)
PYTHON_FREECAD_DIR=$PYTHON_PACKAGES_DIR/freecad

mkdir -p $PYTHON_FREECAD_DIR
mkdir freecad-build
cd freecad-build

cmake -G Ninja \
      -DCMAKE_BUILD_TYPE=Release \
      -DBUILD_QT5=TRUE \
      -DBUILD_GUI=TRUE \
      -DBUILD_FEM=FALSE \
      -DBUILD_SANDBOX=FALSE \
      -DBUILD_TEMPLATE=FALSE \
      -DBUILD_ADDONMGR=FALSE \
      -DBUILD_ARCH=FALSE \
      -DBUILD_ASSEMBLY=FALSE \
      -DBUILD_COMPLETE=FALSE \
      -DBUILD_DRAFT=FALSE \
      -DBUILD_DRAWING=FALSE \
      -DBUILD_IDF=FALSE \
      -DBUILD_IMAGE=FALSE \
      -DBUILD_IMPORT=FALSE \
      -DBUILD_INSPECTION=FALSE \
      -DBUILD_JTREADER=FALSE \
      -DBUILD_MATERIAL=FALSE \
      -DBUILD_MESH=FALSE \
      -DBUILD_MESH_PART=FALSE \
      -DBUILD_FLAT_MESH=FALSE \
      -DBUILD_OPENSCAD=FALSE \
      -DBUILD_PART=TRUE \
      -DBUILD_PART_DESIGN=FALSE \
      -DBUILD_PATH=FALSE \
      -DBUILD_PLOT=FALSE \
      -DBUILD_POINTS=FALSE \
      -DBUILD_RAYTRACING=FALSE \
      -DBUILD_REVERSEENGINEERING=FALSE \
      -DBUILD_ROBOT=FALSE \
      -DBUILD_SHIP=FALSE \
      -DBUILD_SHOW=TRUE \
      -DBUILD_SKETCHER=FALSE \
      -DBUILD_SPREADSHEET=FALSE \
      -DBUILD_START=FALSE \
      -DBUILD_TEST=FALSE \
      -DBUILD_TECHDRAW=FALSE \
      -DBUILD_TUX=FALSE \
      -DBUILD_WEB=FALSE \
      -DBUILD_SURFACE=FALSE \
      -DBUILD_VR=FALSE \
      -DBUILD_CLOUD=FALSE \
      -DFREECAD_USE_PYBIND11:BOOL=ON \
      -DPYTHON_EXECUTABLE=$PYTHON_BIN \
      -DCMAKE_INSTALL_PREFIX=$PYTHON_FREECAD_DIR \
      -DPYSIDE_LIBRARY=$PYTHON_PACKAGES_DIR/PySide2/libpyside2.abi3.so.5.15 \
      -DPYSIDE2UICBINARY=$PYTHON_PACKAGES_DIR/PySide2/uic \
      -DPYSIDE2RCCBINARY=$PYTHON_PACKAGES_DIR/PySide2/rcc \
      -DFREECAD_USE_EXTERNAL_ZIPIOS=TRUE \
      -DINSTALL_TO_SITEPACKAGES=TRUE \
      ../freecad-source

      # -DPYSIDE_INCLUDE_DIR=/usr/include/PySide2 \
      # -DCMAKE_PREFIX_PATH=/usr/local/Qt-5.15.5/lib/cmake \
ninja install

# Installing lib into different location so overwrite init
echo "import os
import sys

sys.path += __path__
sys.path += [os.path.join(__path__[0], 'lib')]
import FreeCAD as app" > $PYTHON_FREECAD_DIR/__init__.py
