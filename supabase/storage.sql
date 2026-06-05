-- Supabase Storage setup for backend uploads.
-- The Flask app uploads with SUPABASE_SERVICE_ROLE_KEY, so the service role bypasses RLS.
-- Keep the service role key only in Vercel environment variables, never in browser JS.

insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values (
  'barage-uploads',
  'barage-uploads',
  true,
  8388608,
  array['image/png', 'image/jpeg', 'image/gif', 'image/webp']
)
on conflict (id) do update set
  public = excluded.public,
  file_size_limit = excluded.file_size_limit,
  allowed_mime_types = excluded.allowed_mime_types;

-- Optional public-read policy. Public buckets normally serve public URLs,
-- but this makes the intention explicit for projects with stricter defaults.
drop policy if exists "Public read Barage uploads" on storage.objects;
create policy "Public read Barage uploads"
on storage.objects
for select
to public
using (bucket_id = 'barage-uploads');
