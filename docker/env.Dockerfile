FROM ubuntu:latest AS base

ENV DEBIAN_FRONTEND noninteractive

RUN apt-get update \
    && apt-get upgrade -y \
    && apt-get install -y \
        python3-dev \
        python3-venv \
        build-essential \
        software-properties-common \
        cmake \
        git

ENV VIRTUAL_ENV=/opt/venv
RUN python3 -m venv ${VIRTUAL_ENV}
ENV PATH "${VIRTUAL_ENV}/bin:$PATH"

WORKDIR /opt/bluemira

# Build and install Qt5 (5.15.5)
FROM base as build_deps

# Build and install freecad (0.20.0)
COPY scripts/freecad/step1 ./scripts/freecad/step1
RUN bash scripts/freecad/step1/install-freecad-deps.sh \
    && bash scripts/freecad/step1/clone-freecad.sh

COPY scripts/qt5/step1 ./scripts/qt5/step1
RUN bash scripts/qt5/step1/install-qt5-deps.sh
RUN python3 -m pip install --upgrade pip setuptools wheel packaging pybind11-global
RUN apt-get install -y qtbase5-dev qt5-qmake libqt5xmlpatterns5-dev libcoin-dev libqt5svg5-dev qttools5-dev libqt5x11extras5-dev qtbase5-private-dev qttranslations5-l10n

# Build Pyside2
COPY scripts/pyside2/clone-pyside2.sh ./scripts/pyside2/clone-pyside2.sh
RUN bash scripts/pyside2/clone-pyside2.sh

COPY scripts/pyside2/install-pyside2.sh ./scripts/pyside2/install-pyside2.sh
RUN bash scripts/pyside2/install-pyside2.sh

# Build and install pivy (0.6.7)
COPY scripts/pivy/step1 ./scripts/pivy/step1
RUN bash scripts/pivy/step1/clone_pivy.sh && \
 bash scripts/pivy/step1/install-pivy-deps.sh

# Build and install pivy (0.6.7)
COPY scripts/pivy/step2 ./scripts/pivy/step2
RUN bash scripts/pivy/step2/install-pivy.sh

COPY scripts/freecad/install-freecad.sh ./scripts/freecad/install-freecad.sh
RUN bash scripts/freecad/install-freecad.sh

COPY requirements.txt .
# Update and install dependencies available through pip
RUN pip install -i https://test.pypi.org/simple/ 'CoolProp==6.4.2.dev0' \
    && python -m pip install -r requirements.txt
# Coolprop numba-scipy neutronics-materal-maker

# Build and install fenicsx
COPY scripts/fenicsx ./scripts/fenicsx/
RUN bash scripts/fenicsx/install-fenicsx-deps.sh
RUN bash scripts/fenicsx/install-fenicsx.sh

FROM base as release
COPY --from=build_deps /usr /usr
COPY --from=build_deps /etc /etc

RUN useradd -ms /bin/bash user
COPY --from=build_deps --chown=user /opt/venv/ /opt/venv/
RUN chown user:user /opt/venv
USER user
WORKDIR /home/user

FROM release as develop
COPY requirements-develop.txt .
RUN pip install --no-cache-dir -r requirements-develop.txt
