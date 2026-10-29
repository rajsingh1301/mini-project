import { useCallback, useRef, useState } from "react";
import { fitSize } from "../lib/guidance.js";

/**
 * Back camera at high resolution. Walking frames are downscaled to 640 px for
 * speed; reading frames keep full resolution so small print stays legible.
 */
export function useCamera() {
  const videoRef = useRef(null);
  const streamRef = useRef(null);
  const canvases = useRef({});
  const [torchSupported, setTorchSupported] = useState(false);

  const start = useCallback(async () => {
    const stream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: { ideal: "environment" }, width: { ideal: 1920 }, height: { ideal: 1080 } },
      audio: false,
    });
    streamRef.current = stream;
    const video = videoRef.current;
    video.srcObject = stream;
    await video.play();
    const track = stream.getVideoTracks()[0];
    const caps = track.getCapabilities ? track.getCapabilities() : {};
    setTorchSupported(Boolean(caps.torch));
  }, []);

  const stop = useCallback(() => {
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
    if (videoRef.current) videoRef.current.srcObject = null;
    setTorchSupported(false);
  }, []);

  /** JPEG of the current frame; each `slot` has its own canvas so captures never collide. */
  const capture = useCallback((maxSide, quality, slot) => {
    const video = videoRef.current;
    if (!video || !video.videoWidth) return Promise.resolve(null);
    const { width, height } = fitSize(video.videoWidth, video.videoHeight, maxSide);
    const canvas = (canvases.current[slot] ||= document.createElement("canvas"));
    canvas.width = width;
    canvas.height = height;
    canvas.getContext("2d").drawImage(video, 0, 0, width, height);
    return new Promise((resolve) =>
      canvas.toBlob((blob) => resolve(blob ? { blob, width, height } : null), "image/jpeg", quality));
  }, []);

  /** Phone flashlight, where the browser allows it (Android Chrome). */
  const setTorch = useCallback(async (on) => {
    const track = streamRef.current?.getVideoTracks()[0];
    if (!track) return false;
    try {
      await track.applyConstraints({ advanced: [{ torch: on }] });
      return true;
    } catch {
      return false;
    }
  }, []);

  return { videoRef, start, stop, capture, setTorch, torchSupported };
}
