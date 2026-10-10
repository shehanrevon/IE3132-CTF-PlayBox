# Stage 2 hints (add in CTFd, each with a point cost)

| # | Cost | Hint |
|---|------|------|
| 1 | 0-5 pts | Most of this capture is boring office traffic. Look for the one conversation that does not belong (odd hostname, odd port). |
| 2 | 10 pts  | In Wireshark: `http.request.method == "POST"` then right-click -> Follow -> TCP Stream. One upload is unreadable bytes. |
| 3 | 15 pts  | Read the upload's HTTP headers. The body is XOR-encrypted with a repeating key: your answer from the previous case file, exactly as submitted (CyberChef: "XOR", key type UTF8). |
