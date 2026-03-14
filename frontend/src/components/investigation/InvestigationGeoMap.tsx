import { useMemo } from 'react'
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet'
import { Paper, Typography } from '@mui/material'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { GraphNode } from '../../types'

// Fix default marker icon in react-leaflet
delete (L.Icon.Default.prototype as any)._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
})

interface InvestigationGeoMapProps {
  nodes: GraphNode[]
}

const InvestigationGeoMap = ({ nodes }: InvestigationGeoMapProps) => {
  const markers = useMemo(() => {
    return nodes
      .filter((n) => {
        const d = n.data as Record<string, unknown>
        return d?.type === 'ip' && d?.latitude != null && d?.longitude != null
      })
      .map((n) => {
        const d = n.data as Record<string, unknown>
        return {
          ip: String(d.address ?? d.id ?? ''),
          lat: Number(d.latitude),
          lng: Number(d.longitude),
          city: d.city as string | undefined,
          country: d.country as string | undefined,
        }
      })
  }, [nodes])

  if (markers.length === 0) {
    return (
      <Paper sx={{ p: 3, textAlign: 'center' }}>
        <Typography color="text.secondary" variant="body2">
          No geolocation data. Run GeoIP enricher on IP nodes.
        </Typography>
      </Paper>
    )
  }

  const center: [number, number] =
    markers.length === 1
      ? [markers[0].lat, markers[0].lng]
      : [
          markers.reduce((s, m) => s + m.lat, 0) / markers.length,
          markers.reduce((s, m) => s + m.lng, 0) / markers.length,
        ]

  return (
    <Paper sx={{ overflow: 'hidden', borderRadius: 2 }}>
      <MapContainer
        center={center}
        zoom={markers.length === 1 ? 8 : 3}
        style={{ height: 280, width: '100%' }}
        scrollWheelZoom
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        {markers.map((m) => (
          <Marker key={m.ip} position={[m.lat, m.lng]}>
            <Popup>
              <strong>{m.ip}</strong>
              <br />
              {[m.city, m.country].filter(Boolean).join(', ')}
            </Popup>
          </Marker>
        ))}
      </MapContainer>
    </Paper>
  )
}

export default InvestigationGeoMap
