import { invokeWithFallback, sidecarPost } from "@/services/tauri";

export interface ImageOption {
  src: string;
  source: string;
  title: string;
  page_url: string;
}

export interface ImageSearchRequest {
  query: string;
  page: number;
  page_size: number;
}

export interface ImageSearchResponse {
  query: string;
  page: number;
  page_size: number;
  options: ImageOption[];
  next_page: number | null;
  has_more: boolean;
  error: string;
}

export async function searchImages(
  request: ImageSearchRequest,
): Promise<ImageSearchResponse> {
  return invokeWithFallback<ImageSearchResponse>(
    "search_images",
    { payload: request },
    async () => sidecarPost<ImageSearchResponse>("/images", request),
  );
}
