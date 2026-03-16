# Where to Paste Your Session

**No password.** Session only. Persists across restarts.

---

## 1. Get your session cookies

1. Log in to [substack.com](https://substack.com) (with Google, magic link, etc.).
2. Open DevTools (F12 or Cmd+Option+I).
3. Go to **Application** → **Cookies** → `https://substack.com`.
4. Copy the **Value** for:
   - `substack.sid`
   - `connect.sid`

---

## 2. Paste into `.env`

Edit `newsletter/scripts/.env`:

```
SUBSTACK_COOKIES=substack.sid=PASTE_VALUE_1_HERE; connect.sid=PASTE_VALUE_2_HERE
SUBSTACK_PUBLICATION=https://systemdesignlaws.substack.com
SUBSTACK_EMAIL=jimmymalhan999@gmail.com
```

Replace `PASTE_VALUE_1_HERE` and `PASTE_VALUE_2_HERE` with the actual values. Keep the semicolon between them.

---

## 3. Session persistence

On first successful run, the script saves the session to `.substack-session.json`. Future runs use that file — no need to paste again until the session expires.

When the session expires, paste fresh cookies into `.env` and run again. The script will refresh `.substack-session.json`.

---

## 4. Run

```bash
cd newsletter/scripts
pip install -r requirements.txt
python create_draft.py --draft scaling-reads-for-system-design-interviews.md
```

The script outputs an **Edit** link (e.g. `https://jimmymalhan.substack.com/publish/post/123456`). Open it in a browser while logged in to Substack to edit the draft directly. This link works for sharing or bookmarking.
