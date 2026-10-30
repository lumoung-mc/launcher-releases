# 루뭉S2 런처 배포 정보

`details.json`은 런처와 게임 목록, 공지, 패치노트, 이미지·영상 주소,
위키 내용을 담는 파일입니다.

## 파일 구성

```text
details.json
games/cleancity/assets/
  logo.png
  thumbnail.png
  background.mp4
games/cleancity/manifest.json
games/cleancity/minecraft/
  options.txt
  mods/
tools/build_manifest.py
```

- `id`: 내부 식별자. `cleancity`를 유지합니다.
- `name`: 화면에 표시할 이름. 현재 요청에 맞춰 `쓱싹서버`로 작성했습니다.
- `launcher_version`: 최신 런처 버전입니다.
- `launcher_update`: 설치용 EXE의 `url`, `sha256`, `size`입니다.
  설치된 런처보다 최신 버전일 때 다운로드와 검증 후 자동 설치합니다.
- `version`: 게임 배포 버전입니다.
- `notices`, `patch_notes`: 게시물 URL 목록입니다. 빈 배열은 등록된 글이 없다는 뜻입니다.
- `manifest_url`: 커밋으로 고정된 `games/cleancity/manifest.json` 주소입니다.
- `assets`: GitHub의 원본 파일을 직접 받는 HTTPS 주소입니다.
- `wiki`: 분류 목록입니다. 각 분류는 `title`과 `articles`를 갖습니다.
  글은 `title`, `body`, 선택적인 표 데이터 `rows`를 갖습니다.
  표의 각 행은 `label`, `value`로 구성합니다.

## GitHub에 올리기

현재 파일 주소는 **lumoung-mc/launcher-releases 저장소의 main 브랜치**를
기준으로 작성했습니다. 위 폴더 구조를 그대로 업로드해야 하며,
저장소·브랜치가 다르면 `assets`의 주소도 수정해야 합니다.

업로드 후 배포 정보 주소:

```text
https://raw.githubusercontent.com/lumoung-mc/launcher-releases/main/details.json
```

`background.mp4`는 2560×1440, 24fps, 오디오 트랙 없음, 1초 교차 페이드가
이미 포함된 반복용 영상입니다. 런처에서 또 교차 페이드를 적용하지 않습니다.

이 폴더에 파일을 준비하는 것과 GitHub 업로드, 런처 원격 정보 연동은 별도 작업입니다.
런처는 이 저장소에서 게임 정보와 에셋을 가져옵니다.
Minecraft 게임 자체의 설치·실행 기능은 런처 프로그램의 자동 업데이트와 별개입니다.

## 런처 설치

[루뭉S2 런처 1.0.0 설치 파일 다운로드](https://raw.githubusercontent.com/lumoung-mc/launcher-releases/main/launcher/windows/LumoungsLauncher-1.0.0-Setup.exe)

- Windows x64 설치용 EXE이며, GitHub나 개발 도구를 설치할 필요가 없습니다.
- 관리자 권한 없이 현재 사용자 계정에 설치됩니다.
- 설치 위치 기본값: `%LOCALAPPDATA%\Programs\LumoungsLauncher`
- 제공된 프로필 이미지가 앱·설치 프로그램·바탕화면 바로가기 아이콘에 적용됩니다.
- 시작할 때와 실행 중 5분마다 업데이트를 확인합니다.
- 자동 업데이트가 켜져 있으면 다운로드·검증 후 안내하고 10초 뒤 설치·재실행합니다.
- 설정에서 자동 업데이트를 끄거나 직접 업데이트를 확인할 수 있습니다.

배포자는 새 버전 EXE를 새 파일명으로 올리고 `launcher_version`과
`launcher_update`를 함께 갱신해야 합니다. 이미 배포한 버전 파일을 덮어쓰지 않습니다.

## 게임 설치 목록 갱신

Minecraft 26.2, Fabric Loader 0.19.5, Java 25 기준입니다.
Minecraft 본체·라이브러리·Java는 이 폴더에 포함하지 않고 설치기가 따로 준비해야 합니다.

모드 등을 변경한 뒤 다음을 실행하면 파일 크기·SHA-256·다운로드 주소와
`details.json`의 설치 목록 주소가 갱신됩니다.

```powershell
python tools/build_manifest.py
```

- `path`: 설치할 Minecraft 인스턴스 폴더 기준 상대 경로입니다.
- `mode: managed`: 배포 버전에 맞춰 내려받고 검증할 파일입니다.
- `mode: install_if_missing`: 없을 때만 설치하며 기존 사용자 파일을 보존합니다.
  `options.txt`와 기본 `config/` 파일에 적용됩니다.
- 업데이트 중 삭제는 이전 설치 목록에서 관리하던 파일로만 제한해야 합니다.
  임의의 사용자 모드·월드·스크린샷을 일괄 삭제하는 규칙은 아닙니다.
- 파일을 변경해 배포할 때는 `details.json`의 게임 `version`도 올려 주세요.

현재 팩에는 Sodium이 포함되어 있습니다. Vulkan용 파일 구성은 아직 별도로
정의하지 않았으므로 렌더링 모드별 설치 분리는 추후 설치기에서 구성해야 합니다.

## 배포 파일과 캐시

버전별 복사본은 만들지 않습니다. 게임 파일과 설치 목록은 GitHub의 커밋 주소로
고정하여, 캐시가 늦게 갱신되어도 목록과 파일이 섞이지 않게 합니다.

1. `minecraft/` 변경 파일과 게임 버전을 커밋합니다.
2. `python tools/build_manifest.py`로 목록을 만들고 `manifest.json`을 커밋합니다.
3. `python tools/build_manifest.py --pin-manifest`를 실행합니다.
4. `details.json`을 커밋하고 모두 푸시합니다.

SHA-256과 크기는 로컬 줄바꿈 변환이 아닌 실제 Git 커밋의 파일로 계산합니다.
검증: `python -m unittest discover -s tools -p test_build_manifest.py`
