FROM pytorch/pytorch:2.1.0-cuda11.8-cudnn8-runtime
ARG DEBIAN_FRONTEND=noninteractive

ENV USER=user
ENV HOME=/home/$USER
ENV REPO_DIR=$HOME/neurender

USER root

RUN apt update
RUN apt install -y git
RUN apt install -y vim net-tools
# RUN apt install -y awscli  # Don't preinstall -- need to override user-input requirements at install time

# Dependencies necessary for opencv-python
RUN apt install -y ffmpeg libsm6 libxext6


# Build Colmap

ENV QT_XCB_GL_INTEGRATION=xcb_egl

RUN apt install -y \
    cmake \
    ninja-build \
    build-essential

RUN apt install -y \
    libboost-program-options-dev \
    libboost-filesystem-dev \
    libboost-graph-dev \
    libboost-system-dev \
    libeigen3-dev \
    libflann-dev \
    libfreeimage-dev \
    libmetis-dev \
    libgoogle-glog-dev \
    libgtest-dev \
    libsqlite3-dev \
    libglew-dev \
    qtbase5-dev \
    libqt5opengl5-dev \
    libcgal-dev \
    libceres-dev

WORKDIR $HOME/src
RUN git clone https://github.com/colmap/colmap.git
WORKDIR $HOME/src/colmap
RUN git fetch https://github.com/colmap/colmap.git main
RUN git checkout FETCH_HEAD
# RUN git checkout dev
RUN mkdir build
WORKDIR $HOME/src/colmap/build
RUN cmake .. -GNinja -DCMAKE_CUDA_ARCHITECTURES=native

# -j4 is necessary to reduce memory usage, avoiding crash during c++ compilation
RUN ninja -j4
RUN ninja install
WORKDIR $HOME
# RUN rm -rf src/colmap

#####



RUN apt clean

# Replace the system python interpreter with the correct conda python3
# So scripts prefixed with #!/usr/bin/python3 work properly
RUN rm /usr/bin/python3 && ln -s /opt/conda/bin/python3 /usr/bin/python3

# Need to create non-root user
#USER $USER
RUN mkdir -p $HOME

WORKDIR $HOME

# For vastai deployments
RUN pip install vastai boto3
RUN pip install am_imaging


# TODO ensure .profile is executed when user logs in

# Copy this repository into the container
COPY --chown=$USER:$USER . $REPO_DIR

RUN echo 'export PATH=$REPO_DIR/bin:\$PATH' >> .bashrc


#COPY ./gaussian-splatting-build ${BUILD_DIR}

# Install Gaussian Splatting dependencies
WORKDIR $REPO_DIR/tools/gaussian-splatting-build

RUN pip install -r requirements.txt

WORKDIR $HOME

# Note: not --recursive because we aren't building the dependencies in this step
#RUN git clone https://github.com/graphdeco-inria/gaussian-splatting 

WORKDIR $HOME

# COPY --chown=$USER:$USER bin bin

