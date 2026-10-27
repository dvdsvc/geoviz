export interface PageImage {
  page: number;
  image: string;
  width: number;
  height: number;
  dpi: number;
}

export interface ProvenanceField {
  data_type: string;
  record_id: string;
  label: string;
  display: string;
  page: number | null;
  bbox: [number, number, number, number] | null;
  bbox_norm: [number, number, number, number] | null;
  matched_text: string;
  match_type: string;
}

export interface ProvenanceData {
  paper_name: string;
  pdf_path: string;
  total_pages: number;
  total_fields: number;
  found_count: number;
  not_found_count: number;
  page_images: PageImage[];
  provenances: ProvenanceField[];
}

export interface PaperInfo {
  paper_name: string;
  short_name: string;
  total_pages: number;
  total_fields: number;
  found_count: number;
}
