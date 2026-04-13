# [트러블슈팅] ECONNREFUSED — Vite 프록시 연결 거부

> 작성일: 2026-04-13  
> 프로젝트: RAG 기반 연애 상담 챗봇  
> 스택: React · Vite · FastAPI

---

## 문제 상황

포트 충돌 문제를 해결하기 위해 Vite 프록시 타겟을 `8001`로 변경한 직후,  
프론트 터미널에서 아래 에러가 반복 출력됐다.

```
PM 5:50:38 [vite] http proxy error: /api/sessions/
AggregateError [ECONNREFUSED]:
    at internalConnectMultiple (node:net:1134:18)
    at afterConnectMultiple (node:net:1715:7) (x2)
```

---

## ECONNREFUSED 란?

`ECONNREFUSED`는 **"연결 거부됨(Connection Refused)"** 을 의미하는 Node.js 네트워크 에러다.  
OS 수준에서 해당 포트에 바인딩된 프로세스가 없을 때, TCP 핸드셰이크 과정에서 즉시 RST 패킷을 반환하며 발생한다.

### Vite 프록시 동작 흐름

```
브라우저
  │  GET /api/sessions/
  ▼
Vite Dev Server (port 5173)
  │  프록시: /api → http://localhost:8001
  ▼
localhost:8001  ← 여기에 아무것도 없음
  │
  ✕ ECONNREFUSED
```

### ECONNREFUSED vs ETIMEDOUT 비교

| 에러 | 상황 | 의미 |
|------|------|------|
| `ECONNREFUSED` | 포트에 서버가 없음 | OS가 즉시 연결 거부 |
| `ETIMEDOUT` | 서버가 있지만 응답 없음 | 지정된 시간 내 응답 없음 |
| `ENOTFOUND` | 호스트명 자체를 찾을 수 없음 | DNS 해석 실패 |

ECONNREFUSED는 세 가지 중 가장 명확한 에러다.  
서버가 느린 게 아니라 **아예 존재하지 않는다**는 뜻이다.

---

## 원인

Vite 프록시 타겟을 `http://localhost:8001`로 변경했지만,  
백엔드 서버가 아직 **8001 포트로 재시작되지 않은 상태**였다.

```
# vite.config.ts (변경 후)
proxy: {
  '/api': {
    target: 'http://localhost:8001',  ← 8001을 바라봄
  }
}
```

```bash
# 실제 실행 중인 서버
uvicorn running on http://127.0.0.1:8000  ← 8000에서 실행 중
# 8001 포트: 비어있음
```

프록시 설정과 실제 서버 포트가 불일치한 상태였다.

---

## 해결 방법

백엔드를 8001 포트로 재시작한다.

```bash
# 기존 서버 종료 후
uvicorn app.main:app --reload --port 8001
```

정상 실행 시 출력:

```
INFO:     Uvicorn running on http://127.0.0.1:8001 (Press CTRL+C to quit)
INFO:     Started reloader process using WatchFiles
INFO:     Application startup complete.
```

이후 Vite 프록시가 8001로 정상 연결되어 에러가 사라진다.

---

## 교훈

Vite 프록시 설정(`vite.config.ts`)을 변경했다면, **반드시 실제 백엔드 서버 포트와 일치하는지 확인**한다.  
포트 불일치는 ECONNREFUSED로 바로 드러나지만, 혼동하기 쉬운 실수다.

```
vite.config.ts의 target 포트 == 실제 uvicorn 실행 포트
```
