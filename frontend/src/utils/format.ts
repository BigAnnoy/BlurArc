/**
 * 格式化文件大小
 * - < 1 GB 时显示为 MB
 * - >= 1 GB 时显示为 GB
 */
export function formatSize(sizeMb: number): string {
  if (sizeMb < 1024) {
    return `${sizeMb.toFixed(1)} MB`;
  }
  return `${(sizeMb / 1024).toFixed(2)} GB`;
}
