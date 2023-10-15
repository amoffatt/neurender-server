FROM dromni/nerfstudio:0.3.4
ARG DEBIAN_FRONTEND=noninteractive

ENV USER=user
ENV HOME=/home/$USER
ENV REPO_DIR=$HOME/neurender

USER root

RUN apt update
RUN apt install -y git vim net-tools imagemagick
# RUN apt install -y awscli  # Don't preinstall -- need to override user-input requirements at install time

# Dependencies necessary for opencv-python
# RUN apt install -y ffmpeg libsm6 libxext6


## Install/Build Colmap

# apt install version requires GUI. getting to work with xvfb would take extra debugging. Just building from source with GUI_ENABLED=OFF instead
#RUN apt install -y colmap

# ENV QT_XCB_GL_INTEGRATION=xcb_egl

# RUN apt install -y \
#     cmake \
#     ninja-build \
#     build-essential

# RUN apt install -y \
#     libboost-program-options-dev \
#     libboost-filesystem-dev \
#     libboost-graph-dev \
#     libboost-system-dev \
#     libeigen3-dev \
#     libflann-dev \
#     libfreeimage-dev \
#     libmetis-dev \
#     libgoogle-glog-dev \
#     libgtest-dev \
#     libsqlite3-dev \
#     libglew-dev \
#     qtbase5-dev \
#     libqt5opengl5-dev \
#     libcgal-dev \
#     libceres-dev

# WORKDIR $HOME/src
# RUN git clone https://github.com/colmap/colmap.git
# WORKDIR $HOME/src/colmap
# RUN git fetch https://github.com/colmap/colmap.git main
# RUN git checkout FETCH_HEAD
# # RUN git checkout dev
# RUN mkdir build
# WORKDIR $HOME/src/colmap/build
# RUN cmake .. -GNinja -DCMAKE_CUDA_ARCHITECTURES=all-major -DGUI_ENABLED=OFF

# # -j6 is necessary to reduce memory usage, avoiding crash during c++ compilation
# RUN ninja -j6
# RUN ninja install
# WORKDIR $HOME
# # RUN rm -rf src/colmap

#####



RUN apt clean

# Replace the system python interpreter with the correct conda python3
# So scripts prefixed with #!/usr/bin/python3 work properly
# RUN rm /usr/bin/python3 && ln -s /opt/conda/bin/python3 /usr/bin/python3

# Need to create non-root user
#USER $USER
# RUN mkdir -p $HOME

WORKDIR $HOME

# RUN pip install nerfstudio

# For vastai deployments
RUN pip install vastai boto3

RUN pip install am_imaging pydantic pydantic_yaml
# RUN pip uninstall -y opencv-python
# RUN pip install opencv-python-headless


# TODO ensure .profile is executed when user logs in

# Copy this repository into the container
COPY --chown=$USER:$USER . $REPO_DIR

RUN echo 'export PATH=${REPO_DIR}/bin:$PATH' >> .bashrc

# ensure CUDA tools are on the path
# RUN echo 'export PATH=/usr/local/cuda/bin:$PATH' >> .bashrc
# RUN echo 'export LD_LIBRARY_PATH=/usr/local/cuda/lib64/:$LD_LIBRARY_PATH' >> .bashrc

# Avoid error in colmap
# RUN echo 'export MKL_THREADING_LAYER=GNU' >> .bashrc


#COPY ./gaussian-splatting-build ${BUILD_DIR}

# Install Gaussian Splatting dependencies
WORKDIR $REPO_DIR/tools/gaussian-splatting-build
RUN pip install -r requirements.txt

# Install gaussian splatting build of nerfstudio
# Necessary for rendering camera paths to video
WORKDIR $REPO_DIR/tools/nerfstudio-gaussian-splatting-fork
RUN pip uninstall -y nerfstudio
RUN pip install --upgrade pip setuptools 
RUN pip install -e .

# Note: not --recursive because we aren't building the dependencies in this step
#RUN git clone https://github.com/graphdeco-inria/gaussian-splatting 

WORKDIR $HOME

RUN pip install -e neurender

# COPY --chown=$USER:$USER bin bin

ENTRYPOINT [ "/home/user/neurender/run-shutdown-timer.sh" ]

