# The Fedora 44 gate in reviews/321-deskflow-image/PROGRESS.md.
deskflow_nevra=deskflow-0:1.27.0-1.fc44.x86_64
deskflow_sha256=21a404d8bd0488fdc7ec635ed26447d623b132dc4ae3d12e5f944991ab76484b
fedora_repos=(--disable-repo='*' --enable-repo=fedora --enable-repo=updates
              --setopt=install_weak_deps=False --setopt=skip_if_unavailable=False --setopt=gpgcheck=True)

deskflow_repos() {
    local stable
    if [[ $1 == throwaway ]]; then
        stable=$(dnf5 "${fedora_repos[@]}" repoquery --qf '%{full_nevra}' "$deskflow_nevra") || return
        if ! grep -Fxq "$deskflow_nevra" <<<"$stable"; then
            fedora_repos+=(--enable-repo=updates-testing --setopt="updates-testing.includepkgs=$deskflow_nevra")
        fi
    fi
}

check_deskflow_rpm() {
    local files=("$1"/deskflow-*.rpm) actual
    [[ ${#files[@]} == 1 && -f ${files[0]} ]] || return 1
    actual=$(rpm -qp --qf '%{NAME}-%{EPOCHNUM}:%{VERSION}-%{RELEASE}.%{ARCH}' "${files[0]}") || return
    [[ $actual == "$deskflow_nevra" ]] || return 1
    printf '%s  %s\n' "$deskflow_sha256" "${files[0]}" | sha256sum -c -
}

resolve_deskflow_candidate() {
    local mode=$1 dest=$2 match repo other
    local -a exclude=()
    shift 2
    if [[ $mode == resolve ]]; then
        deskflow_repos throwaway || return
    fi
    match=$(dnf5 "${fedora_repos[@]}" repoquery --available --qf '%{full_nevra} %{repoid}\n' "$deskflow_nevra") || return
    case $match in
        "$deskflow_nevra fedora"|"$deskflow_nevra updates"|"$deskflow_nevra updates-testing")
            repo=${match##* }
            ;;
        *)
            printf 'Cannot identify one Fedora repository for the reviewed Deskflow RPM: %s\n' "$match" >&2
            return 1
            ;;
    esac
    if [[ $mode == resolve-deskflow-stable && $repo != updates ]]; then
        printf 'Deskflow requires Fedora stable updates, found %s\n' "$repo" >&2
        return 1
    fi
    # Keep all dependency repositories, but make only the recorded one eligible to serve Deskflow.
    for other in fedora updates updates-testing; do
        if [[ $other != "$repo" ]]; then
            exclude+=("--setopt=$other.excludepkgs=deskflow")
        fi
    done
    dnf5 "${fedora_repos[@]}" "${exclude[@]}" download --resolve --destdir="$dest" "$@" "$deskflow_nevra" >&2 &&
        check_deskflow_rpm "$dest" >&2 || return 1
    printf 'DESKFLOW_RESOLVED repo=%s nevra=%s sha256=%s\n' "$repo" "$deskflow_nevra" "$deskflow_sha256"
}
