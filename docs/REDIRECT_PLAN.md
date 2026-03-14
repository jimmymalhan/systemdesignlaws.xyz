# Substack Redirect Plan: One Landing Page Only

## Goal

Keep **one canonical page** (systemdesignlaws.xyz) for visitors. When people visit the old Substack landing (newsletter.systemdesignlaws.xyz), redirect them to your custom page.

## Current Setup

- **systemdesignlaws.xyz** → Custom landing page (this repo, GitHub Pages)
- **newsletter.systemdesignlaws.xyz** → Substack default page ("This newsletter is easy to follow...")
- **systemdesignlaws.substack.com** → Same Substack (fallback when custom domain removed)

## Plan (Order Matters)

### Step 1: Remove Custom Domain from Substack

1. Go to [Substack Dashboard](https://substack.com) → Your publication → **Settings** → **Domain**
2. **Remove** `newsletter.systemdesignlaws.xyz` as the custom domain
3. Substack will revert to `systemdesignlaws.substack.com` for all subscription and post URLs
4. DNS for `newsletter.systemdesignlaws.xyz` will be free for you to use

### Step 2: Deploy Redirect at newsletter.systemdesignlaws.xyz

Option A – **New GitHub Repo** (recommended):

1. Create a new repo (e.g. `systemdesignlaws-newsletter-redirect`)
2. Copy the contents of `newsletter-redirect/` from this repo
3. Enable GitHub Pages (Settings → Pages → Source: main branch)
4. Add custom domain: `newsletter.systemdesignlaws.xyz`
5. Add CNAME: `newsletter.systemdesignlaws.xyz` (GitHub will show the correct CNAME target)
6. Point your DNS: `newsletter.systemdesignlaws.xyz` → GitHub Pages (or `username.github.io`)

Option B – **Netlify**:

1. Create Netlify site from the `newsletter-redirect/` folder
2. Add custom domain `newsletter.systemdesignlaws.xyz`
3. Point DNS CNAME to Netlify’s load balancer

### Step 3: Codebase Updates (This Repo)

All links to `newsletter.systemdesignlaws.xyz` are updated to `systemdesignlaws.substack.com`:

- Subscribe buttons → systemdesignlaws.substack.com
- Post links in Recent Issues → systemdesignlaws.substack.com/p/...
- RSS feed (CI) → systemdesignlaws.substack.com/feed
- Footer links → systemdesignlaws.substack.com

### Step 4: Verify

1. Visit **newsletter.systemdesignlaws.xyz** → should redirect to **systemdesignlaws.xyz**
2. Visit **systemdesignlaws.xyz** → see your custom page
3. Click **Subscribe** → goes to systemdesignlaws.substack.com subscription flow
4. Click article links → open posts on systemdesignlaws.substack.com

## Result

- **One landing page**: systemdesignlaws.xyz
- **Old Substack URL redirects** to it
- **Subscription and posts** live on systemdesignlaws.substack.com

## Troubleshooting

**RSS feed**: After removing the custom domain, the feed should be at `https://systemdesignlaws.substack.com/feed`. If the CI "Update Recent Posts" workflow fails, verify the feed URL in Substack Settings or run `curl -sL "https://systemdesignlaws.substack.com/feed" -o feed.xml` locally to test.
