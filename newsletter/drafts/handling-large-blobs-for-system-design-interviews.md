# Handling Large Blobs

**TL;DR** - Files should never pass through your application server. Use presigned URLs for direct upload to object storage, multipart upload for files over 5MB, resumable upload for unreliable networks, and CDN for downloads. The server handles metadata and authorization only.

>> 30-second elevator pitch: "Large files bypass my application server entirely. Clients get a presigned URL and upload directly to S3 in chunks. An S3 event triggers async processing like thumbnails or transcoding. Downloads go through a CDN. My server only handles metadata and authorization."

---

## What You Will Learn

> **Upload Patterns**
> - Presigned URL upload (bypass application server)
> - Multipart upload (parallel chunks for large files)
> - Resumable upload (recover from network failures)
> - Progress tracking (chunk completion percentage)
>
> **Download Patterns**
> - CDN edge caching (global distribution)
> - Presigned URL download (private file access)
> - Adaptive bitrate streaming (video)
>
> **Processing Patterns**
> - Thumbnail generation pipeline (eager, lazy, hybrid)
> - Video transcoding pipeline (multi-resolution, HLS)
> - Content-addressable storage and deduplication
>
> **Deep Dives**
> - Abuse prevention and quota systems
> - Upload failure recovery and state machines
> - Cloud provider comparison (S3, GCS, Azure Blob)

---

## The Problem

Your users need to upload and download files: profile photos, videos, documents, data exports. The naive approach routes everything through your application server. A 500MB video upload consumes server memory, CPU, and bandwidth for minutes. During that time, the server cannot handle other requests. Multiply by thousands of concurrent uploads and your entire system grinds to a halt.

![Naive Upload: Through the App Server](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/lb-naive-upload.svg)

The file passes through your server twice: once from client to server, once from server to storage. That doubles bandwidth consumption and ties up server resources for the entire transfer duration.

>> Every system design that involves user-generated content (images, videos, documents) needs a blob storage strategy. The patterns are the same whether you are designing Dropbox, YouTube, Instagram, or Slack.

**5 problems that use this pattern:** Dropbox, YouTube, Instagram, Slack file sharing, Google Drive.

---

## The Solution: Direct Upload with Presigned URLs

The core insight: your application server should never touch the file data. Instead, it generates a short-lived presigned URL that grants the client temporary permission to upload directly to object storage.

![Presigned URL Upload Flow](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/lb-presigned-url-upload.svg)

The flow is straightforward. The client requests an upload URL from your API. Your server validates the request (authentication, file type, quota check), generates a presigned URL from S3, and returns it. The client uploads directly to S3 using that URL. Your server never sees the file bytes.

![Direct vs Proxy Upload](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/lb-direct-vs-proxy.svg)

> **What interviewers want to hear:** "The file never passes through my application server. I use presigned URLs so the client uploads directly to object storage. My server only handles metadata and authorization."

---

## Multipart Upload

For files larger than 5MB, a single PUT request is risky. Network interruptions mean starting over. Multipart upload splits the file into chunks that upload independently, often in parallel.

![Multipart Upload: Parallel Chunks](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/lb-multipart-upload.svg)

The process works in three phases. Initiate: the client tells S3 to start a multipart upload and receives an upload ID. Upload parts: the client splits the file into chunks (typically 5-100MB each) and uploads them in parallel, each getting its own presigned URL. Each completed part returns an ETag. Complete: the client sends all ETags to S3, which assembles the final object.

![Chunk Parallel Upload](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/lb-chunk-parallel.svg)

> **Benefits:** Parallel upload (faster), individual chunk retry (resilient), and progress tracking (user experience).

---

## Resumable Upload

Mobile users on flaky networks need to resume where they left off. Resumable upload tracks which chunks are complete and only re-uploads the missing ones.

![Resumable Upload: Pick Up Where You Left Off](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/lb-resumable-upload.svg)

The server tracks a bitmap of completed chunks per upload ID. When the client reconnects, it queries the server for missing chunks and only uploads those. A 500MB file at 63% completion only needs to upload the remaining 37%.

![Upload Progress Tracking](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/lb-progress-tracking.svg)

---

## Upload Failure Recovery

Uploads can fail at any point. The upload state machine tracks progress and enables recovery.

![Upload State Machine](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/lb-upload-state-machine.svg)

![Upload Failure Recovery](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/lb-upload-failure-recovery.svg)

Incomplete uploads are cleaned up after a configurable expiry (typically 24 hours). S3 lifecycle policies can automatically abort stale multipart uploads.

---

## Metadata and Storage Architecture

The metadata flow separates file data from file information. Object storage holds the actual bytes. Your database holds metadata: filename, size, content type, upload status, owner, access permissions, and references to processed variants (thumbnails, transcoded versions).

![Metadata Flow: Separate Data from Information](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/lb-metadata-flow.svg)

![S3 Architecture: Object Storage Internals](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/lb-s3-architecture.svg)

---

## Downloading: CDN and Presigned URLs

For downloads, the pattern depends on access control. Public content goes through a CDN for global edge caching. Private content uses presigned download URLs with short expiration times.

![CDN Download: Edge Caching for Global Distribution](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/lb-cdn-download.svg)

![Presigned URL Download: Secure Private Access](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/lb-presigned-url-download.svg)

> **Interview tip:** For high-read content (Instagram photos, YouTube videos), always put a CDN in front. The CDN absorbs the read load that would otherwise hit your storage directly.

---

## Processing Pipelines

After a file is uploaded, you often need to process it: generate thumbnails for images, transcode video to multiple resolutions, scan for viruses, or extract metadata.

### Thumbnail Generation

Never process images synchronously in the upload request. Decouple with an event-driven pipeline.

![Thumbnail Generation Pipeline](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/lb-thumbnail-pipeline.svg)

S3 fires a notification on upload completion. A message queue delivers the event to an image worker that generates thumbnails at multiple sizes (150x150, 300x300, 600x600) and converts to WebP. The worker stores output in S3 and updates the metadata database with thumbnail URLs.

### Video Transcoding

Video uploads trigger a transcoding pipeline that produces multiple resolution variants and HLS segments for adaptive bitrate streaming.

![Video Transcoding Pipeline](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/lb-video-transcode-flow.svg)

The pipeline fan-outs: one worker per target resolution. Each worker downloads the raw file, decodes, resizes, encodes, and segments the output. Results go to S3 and CDN.

---

## Content Addressing and Deduplication

For systems like Dropbox where many users might upload the same file, content-addressable storage eliminates duplicates.

![Content-Addressable Storage](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/lb-content-addressing.svg)

The key is the SHA-256 hash of the file content. Same content produces the same hash. Before uploading, check if the hash exists in storage. If it does, skip the upload and just link the user to the existing object. Ten users uploading the same PDF results in one stored copy.

![Deduplication Strategies](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/lb-deduplication.svg)

Chunk-level deduplication goes further: edit one paragraph in a 100MB document, and only the changed 4MB chunk needs re-uploading. This is why Dropbox feels instant for small edits to large files.

---

## Abuse Prevention and Quotas

Without limits, a single user could upload terabytes and bankrupt your storage budget. Implement quotas at multiple levels.

![Abuse Prevention](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/lb-abuse-prevention.svg)

![Quota System](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/lb-quota-system.svg)

Check quotas before generating the presigned URL. Reject oversized files at the API level. Rate-limit upload requests. Scan uploaded content for malware asynchronously.

---

## Real-World Interview Scenarios

![Interview Scenarios: Handling Large Blobs](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/lb-interview-scenarios.svg)

### Dropbox Sync Flow

The Dropbox pattern combines chunked upload, content addressing, and delta sync across devices.

![Dropbox Sync Flow](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/lb-dropbox-flow.svg)

### YouTube Upload Pipeline

YouTube processes 500+ hours of video per minute using resumable upload, fan-out transcoding, and CDN delivery.

![YouTube Upload Pipeline](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/lb-youtube-upload.svg)

---

## Cloud Provider Comparison

The concepts are identical across clouds. Say "object storage" or "S3-compatible storage" in interviews instead of locking to one provider.

![Cloud Provider Object Storage Comparison](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/lb-cloud-provider-comparison.svg)

---

## Decision Tree

![Decision Tree: Choosing an Upload Strategy](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/lb-decision-tree.svg)

> **Start with:** "The file should never pass through our application server." Then layer on complexity based on the specific requirements: file size, reliability needs, processing pipeline, and access patterns.

---

## Summary

![Handling Large Blobs: Summary](https://raw.githubusercontent.com/jimmymalhan/systemdesignlaws.xyz/feature/newsletter-agent-system/newsletter/plots/svg/lb-scaling-summary.svg)

>> The pattern is universal: presigned URL upload, event-driven processing, CDN download. Your application server handles authorization and metadata. Everything else is offloaded to purpose-built infrastructure.

- **Upload** - Presigned URLs for direct-to-storage. Multipart for large files. Resumable for unreliable networks.
- **Processing** - Event-driven pipelines: thumbnails, transcoding, virus scanning, metadata extraction.
- **Download** - CDN for public content. Presigned URLs for private access. Adaptive bitrate for video.
- **Optimization** - Content addressing for deduplication. Chunk-level dedup for delta sync.
- **Protection** - Quotas, rate limits, virus scanning, access control.

In interviews, start with the presigned URL pattern and add complexity based on the problem requirements. Every blob storage problem uses the same core architecture.

{{SUBSCRIBE}}

{{BUTTON:Read More Articles|https://newsletter.systemdesignlaws.xyz}}