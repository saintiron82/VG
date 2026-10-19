# Godot 실행 자산 게시 범위, 2026-10-19

## 바로 실행할 진입점
`godot/riverstone_city/project.godot`은 독립 검사한 이전 배포 도시+원본 Lily 안정본입니다. README와 검증/리소스 manifest는 같은 폴더에 있습니다.

## 기존 경로 보존과 미완료
`Run-City`가 가리키는 기존 preview_r4 경로는 역사적 원본을 보존합니다. 해당 203,027,004-byte scene.json과 270개 render JSON 60,666,067 bytes는 아직 이 Git 저장소에 포함되지 않았습니다. 단일 Git blob 제한을 넘는 scene를 일반 파일로 올리지 않았습니다. 실행은 위 독립 프로젝트를 사용하십시오.

최신 playable_detail_r01/near_detail_r01은 소스가 있으나 50개 native .scn 51,111,881 bytes 외에도 추가 master/sidecar/실험 참조를 요구합니다. 그 동적 의존 전체는 이 커밋에서 독립 복원을 보장하지 않습니다. 소스 누락과 재생성 캐시는 다릅니다. 실험 경로를 이 독립 기본 도시와 같은 완성도로 취급하지 마십시오.

기존 프로젝트의 정적 preload를 복구하기 위해 RenderData.gd/TransformTracks.gd 8개, BridgeFixtureView.gd 2개, RoofNormalFullProof.gd 및 ColorDiagnostic.tscn을 원래 경로에 추가했습니다. 이것만으로 역사적 모든 프로젝트가 실행되지는 않습니다.

첫 소스 게시의 snapshot/source_manifest.json과 preparation_summary/validation은 당시의 기록입니다. snapshot/file_manifest.json은 이번 게시 파일까지 갱신했습니다. tools/verify_snapshot.py는 현재 파일을 검사합니다.
