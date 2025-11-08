/**
 * Utility functions for handling UTC timestamps from the backend
 */

/**
 * Parses a UTC timestamp string and returns a proper Date object.
 *
 * The backend sends UTC timestamps without the 'Z' suffix (e.g., "2025-11-08T23:52:00.217514").
 * JavaScript's Date constructor interprets strings without timezone info as local time,
 * which causes incorrect display. This function ensures timestamps are correctly interpreted as UTC.
 *
 * @param dateString - ISO timestamp string from the backend
 * @returns Date object representing the UTC timestamp
 */
export function parseUTCDate(dateString: string | null | undefined): Date {
  if (!dateString) {
    return new Date()
  }

  // If the string already has a timezone indicator (Z or +/-), use it as-is
  if (dateString.endsWith('Z') || dateString.match(/[+-]\d{2}:\d{2}$/)) {
    return new Date(dateString)
  }

  // Otherwise, append 'Z' to indicate UTC
  return new Date(dateString + 'Z')
}

/**
 * Transforms an object's timestamp fields from strings to Date objects.
 * Useful for transforming API responses with multiple timestamp fields.
 *
 * @param obj - Object containing timestamp fields
 * @param fields - Array of field names to transform
 * @returns New object with transformed timestamps
 */
export function transformTimestamps<T extends Record<string, any>>(
  obj: T,
  fields: (keyof T)[]
): T {
  const result = { ...obj }

  for (const field of fields) {
    if (typeof result[field] === 'string') {
      result[field] = parseUTCDate(result[field] as string) as any
    }
  }

  return result
}
