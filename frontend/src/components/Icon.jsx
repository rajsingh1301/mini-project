/** Small, consistent interface icons. The surrounding control supplies its label. */
export function Icon({ name, ...props }) {
  const paths = {
    eye: <><path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12Z" /><circle cx="12" cy="12" r="3" /></>,
    settings: <><path d="m9 3-.6 2.4-2 .9L4 5.7 2 9l1.8 1.7v2.6L2 15l2 3.3 2.4-.6 2 .9L9 21h4l.6-2.4 2-.9 2.4.6 2-3.3-1.8-1.7v-2.6L20 9l-2-3.3-2.4.6-2-.9L13 3Z" /><circle cx="11" cy="12" r="3" /></>,
    play: <path d="m9 5 11 7-11 7Z" />,
    stop: <rect x="5" y="5" width="14" height="14" rx="2" />,
    scan: <><path d="M8 3H3v5m13-5h5v5M3 16v5h5m13-5v5h-5M8 8h8m-8 4h8m-8 4h5" /></>,
    walk: <><circle cx="14" cy="4" r="2" /><path d="m7 21 4-6 3 3v3M4 12l4-3 4 1 3 4h4m-8-4-1 5m0-5 3-3" /></>,
    repeat: <><path d="M4 10a8 8 0 1 1 1 7M4 4v6h6" /></>,
    volume: <><path d="m11 4-6 5H2v6h3l6 5Zm4 4a6 6 0 0 1 0 8m3-11a10 10 0 0 1 0 14" /></>,
    muted: <><path d="m11 4-6 5H2v6h3l6 5Zm5 5 6 6m0-6-6 6" /></>,
    light: <path d="M9 3h6v4l3 5-4 3v6h-4v-6l-4-3 3-5Zm-2 8h10M9 7h6" />,
    close: <path d="m6 6 12 12M6 18 18 6" />,
    camera: <><path d="M3 7h4l2-3h6l2 3h4v13H3Z" /><circle cx="12" cy="13" r="4" /></>,
  };
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor"
         strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" {...props}>
      {paths[name]}
    </svg>
  );
}
