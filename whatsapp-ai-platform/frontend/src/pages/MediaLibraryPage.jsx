import { useRef } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { UploadCloud, FileText, ImageIcon } from "lucide-react";
import { mediaApi } from "../api/resources";

export default function MediaLibraryPage() {
  const fileInputRef = useRef(null);
  const queryClient = useQueryClient();

  const { data: assets = [], isLoading } = useQuery({ queryKey: ["media"], queryFn: mediaApi.list });

  const uploadMutation = useMutation({
    mutationFn: (file) => mediaApi.upload(file),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["media"] }),
  });

  return (
    <div className="p-6">
      <div className="mb-5 flex items-center justify-between">
        <div>
          <h1 className="font-display text-xl font-semibold text-ink-900">Media library</h1>
          <p className="text-sm text-ink-500">Images and documents your team can send in conversations.</p>
        </div>
        <button
          onClick={() => fileInputRef.current?.click()}
          className="flex items-center gap-2 rounded-lg bg-signal-500 px-4 py-2.5 text-sm font-semibold text-ink-950 hover:bg-signal-400"
        >
          <UploadCloud size={16} /> Upload file
        </button>
        <input
          ref={fileInputRef}
          type="file"
          className="hidden"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) uploadMutation.mutate(file);
            e.target.value = "";
          }}
        />
      </div>

      {uploadMutation.isPending && <p className="mb-3 text-sm text-ink-500">Uploading…</p>}

      {isLoading ? (
        <p className="text-sm text-ink-400">Loading…</p>
      ) : assets.length === 0 ? (
        <div className="rounded-xl border border-dashed border-ink-200 p-10 text-center text-sm text-ink-400">
          No media uploaded yet. Upload an image or PDF to make it available for replies and broadcasts.
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
          {assets.map((asset) => (
            <div key={asset.id} className="overflow-hidden rounded-xl border border-ink-200 bg-white">
              <div className="flex h-32 items-center justify-center bg-ink-50">
                {asset.kind === "image" ? (
                  <img src={asset.url} alt={asset.filename} className="h-full w-full object-cover" />
                ) : (
                  <FileText size={32} className="text-ink-400" />
                )}
              </div>
              <div className="p-2.5">
                <p className="truncate text-xs font-medium text-ink-700">{asset.filename}</p>
                <p className="text-[11px] text-ink-400">{(asset.size_bytes / 1024).toFixed(0)} KB</p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
