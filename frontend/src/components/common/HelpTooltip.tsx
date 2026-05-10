import {
  IconButton,
  Popover,
  Typography,
  Box,
  Dialog,
  DialogTitle,
  DialogContent,
  useTheme,
  useMediaQuery,
} from '@mui/material'
import HelpOutlineIcon from '@mui/icons-material/HelpOutline'
import CloseIcon from '@mui/icons-material/Close'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import type { HelpTopicId } from '../../i18n/locales/helpTopics.en'

export interface HelpContent {
  title: string
  what: string
  whyImportant: string
  whyBad?: string
  tips?: string
}

interface HelpTooltipProps {
  topic: HelpTopicId
  size?: 'small' | 'medium'
}

/** Shared help copy (title rendered separately in dialog header / popover). */
function HelpTopicDetails({
  content,
  t,
}: {
  content: HelpContent
  t: (key: string, options?: Record<string, unknown>) => string
}) {
  return (
    <>
      <Typography variant="body2" paragraph sx={{ mb: 1.5 }}>
        <strong>{t('help.what')}</strong> {content.what}
      </Typography>
      <Typography variant="body2" paragraph sx={{ mb: 1.5 }}>
        <strong>{t('help.whyImportant')}</strong> {content.whyImportant}
      </Typography>
      {content.whyBad && (
        <Typography variant="body2" paragraph sx={{ color: 'error.main', mb: 1.5 }}>
          <strong>{t('help.whyBad')}</strong> {content.whyBad}
        </Typography>
      )}
      {content.tips && (
        <Typography variant="body2" color="text.secondary" component="p" sx={{ m: 0 }}>
          <strong>{t('help.tip')}</strong> {content.tips}
        </Typography>
      )}
    </>
  )
}

const HelpTooltip = ({ topic, size = 'small' }: HelpTooltipProps) => {
  const theme = useTheme()
  const isCompactHelp = useMediaQuery(theme.breakpoints.down('md'), { noSsr: true })
  const { t } = useTranslation()
  const [anchorEl, setAnchorEl] = useState<HTMLElement | null>(null)
  const topicBase = `help.topics.${topic}` as const

  const content: HelpContent = {
    title: t(`${topicBase}.title`),
    what: t(`${topicBase}.what`),
    whyImportant: t(`${topicBase}.whyImportant`),
    whyBad: t(`${topicBase}.whyBad`, { defaultValue: '' }) || undefined,
    tips: t(`${topicBase}.tips`, { defaultValue: '' }) || undefined,
  }

  const handleClick = (e: React.MouseEvent<HTMLElement>) => {
    e.preventDefault()
    e.stopPropagation()
    setAnchorEl(e.currentTarget)
  }

  const handleClose = () => setAnchorEl(null)
  const open = Boolean(anchorEl)

  return (
    <>
      <IconButton
        size={size}
        onClick={handleClick}
        sx={{
          color: 'text.secondary',
          p: 0.25,
          '&:hover': { color: 'primary.main', bgcolor: 'action.hover' },
        }}
        aria-label={t('help.ariaHelp', { title: content.title })}
        aria-expanded={open}
      >
        <HelpOutlineIcon fontSize={size === 'small' ? 'small' : 'medium'} />
      </IconButton>

      {isCompactHelp ? (
        <Dialog
          open={open}
          onClose={handleClose}
          fullWidth
          maxWidth="sm"
          scroll="paper"
          aria-labelledby="help-topic-dialog-title"
          PaperProps={{
            sx: {
              m: { xs: 1, sm: 2 },
              maxHeight: { xs: 'calc(100dvh - 16px)', sm: 'min(90vh, 720px)' },
              display: 'flex',
              flexDirection: 'column',
            },
          }}
        >
          <DialogTitle
            id="help-topic-dialog-title"
            sx={{
              display: 'flex',
              alignItems: 'flex-start',
              justifyContent: 'space-between',
              gap: 1,
              pr: 1,
              py: 1.5,
              typography: 'subtitle1',
              fontWeight: 600,
            }}
          >
            <Box component="span" sx={{ flex: 1, minWidth: 0, pr: 1 }}>
              {content.title}
            </Box>
            <IconButton
              aria-label={t('common.close')}
              onClick={handleClose}
              size="small"
              edge="end"
              sx={{ flexShrink: 0, mt: -0.25 }}
            >
              <CloseIcon fontSize="small" />
            </IconButton>
          </DialogTitle>
          <DialogContent dividers sx={{ py: 2, typography: 'body2' }}>
            <HelpTopicDetails content={content} t={t} />
          </DialogContent>
        </Dialog>
      ) : (
        <Popover
          open={open}
          anchorEl={anchorEl}
          onClose={handleClose}
          anchorOrigin={{ vertical: 'bottom', horizontal: 'left' }}
          transformOrigin={{ vertical: 'top', horizontal: 'left' }}
          marginThreshold={12}
          slotProps={{
            paper: {
              elevation: 4,
              sx: {
                maxWidth: 'min(440px, calc(100vw - 24px))',
                maxHeight: 'min(72vh, 560px)',
                overflow: 'auto',
                p: 2,
                boxSizing: 'border-box',
              },
            },
          }}
        >
          <Box>
            <Typography variant="subtitle1" fontWeight={600} gutterBottom component="h2">
              {content.title}
            </Typography>
            <HelpTopicDetails content={content} t={t} />
          </Box>
        </Popover>
      )}
    </>
  )
}

export default HelpTooltip
