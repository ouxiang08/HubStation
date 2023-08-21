FROM python:3.10.11-alpine AS Builder
RUN apk add --no-cache --virtual .build-deps \
        libffi-dev \
        gcc \
        musl-dev \
        libxml2-dev \
        libxslt-dev \
    && apk add --no-cache $(echo $(wget --no-check-certificate -qO- https://gitee.com/jiajingjing/hub-station/raw/master/package_list.txt)) \
    && ln -sf /usr/bin/python3 /usr/bin/python \
    && curl https://rclone.org/install.sh | bash \
    && if [ "$(uname -m)" = "x86_64" ]; then ARCH=amd64; elif [ "$(uname -m)" = "aarch64" ]; then ARCH=arm64; fi \
    && curl https://dl.min.io/client/mc/release/linux-${ARCH}/mc --create-dirs -o /usr/bin/mc \
    && chmod +x /usr/bin/mc \
    && pip install --upgrade pip setuptools wheel \
    && pip install cython \
    && ls \
    && pip install -r https://raw.githubusercontent.com/ouxiang08/HubStation/master/requirements.txt \
    && apk del --purge .build-deps \
    && rm -rf /tmp/* /root/.cache /var/cache/apk/*
COPY --chmod=755 ./rootfs /
FROM scratch AS APP
COPY --from=Builder / /
COPY --from=Builder / /
ENV S6_SERVICES_GRACETIME=30000 \
    S6_KILL_GRACETIME=60000 \
    S6_CMD_WAIT_FOR_SERVICES_MAXTIME=0 \
    S6_SYNC_DISKS=1 \
    HOME="/nt" \
    TERM="xterm" \
    PATH=${PATH}:/usr/lib/chromium \
    LANG="C.UTF-8" \
    TZ="Asia/Shanghai" \
    HStation_CONFIG="/hubstation/config/config.yaml" \
    HStation_AUTO_UPDATE=true \
    HStation_CN_UPDATE=true \
    HStation_VERSION=master \
    PS1="\u@\h:\w \$ " \
    REPO_URL="https://gitee.com/jiajingjing/hub-station.git" \
    PYPI_MIRROR="https://pypi.tuna.tsinghua.edu.cn/simple" \
    ALPINE_MIRROR="mirrors.ustc.edu.cn" \
    PUID=0 \
    PGID=0 \
    UMASK=000 \
    WORKDIR="/hubstation"
WORKDIR ${WORKDIR}
RUN mkdir ${HOME} \
    && addgroup -S nt -g 911 \
    && adduser -S nt -G nt -h ${HOME} -s /bin/bash -u 911 \
    && python_ver=$(python3 -V | awk '{print $2}') \
    && python_path=$(which python3) \
    && echo "${python_path} <<<<<<<<<<----------------------->>>>>>>>>> ${python_ver}" \
    && [ -d "/usr/lib/python${python_ver%.*}/site-packages" ] || mkdir -p "/usr/lib/python${python_ver%.*}/site-packages" \
    && echo "${WORKDIR}/" > /usr/lib/python${python_ver%.*}/site-packages/hubstation.pth \
    && echo 'fs.inotify.max_user_watches=5242880' >> /etc/sysctl.conf \
    && echo 'fs.inotify.max_user_instances=5242880' >> /etc/sysctl.conf \
    && echo "nt ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers \
    && git config --global pull.ff only \
    && git clone -b master ${REPO_URL} ${WORKDIR} --depth=1 --recurse-submodule \
    && git config --global --add safe.directory ${WORKDIR} \
    && chmod +x /hubstation/docker/entrypoint.sh
EXPOSE 8200
VOLUME ["/config"]
ENTRYPOINT [ "/init" ]
