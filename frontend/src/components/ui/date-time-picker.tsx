"use client"

import * as React from "react"
import { format, isValid, setHours, setMinutes } from "date-fns"
import { CalendarIcon } from "lucide-react"

import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Calendar } from "@/components/ui/calendar"
import { Input } from "@/components/ui/input"
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover"

interface DateTimePickerProps {
  value?: Date
  onChange?: (date: Date | undefined) => void
  placeholder?: string
  className?: string
  disabled?: boolean
}

export function DateTimePicker({
  value,
  onChange,
  placeholder = "Pick date & time",
  className,
  disabled,
}: DateTimePickerProps) {
  const [open, setOpen] = React.useState(false)
  const [time, setTime] = React.useState(() => {
    if (value && isValid(value)) {
      return format(value, "HH:mm")
    }
    return "00:00"
  })

  const handleDateSelect = (date: Date | undefined) => {
    if (!date) {
      onChange?.(undefined)
      return
    }
    const [hours, minutes] = time.split(":").map(Number)
    const dateWithTime = setMinutes(setHours(date, hours || 0), minutes || 0)
    onChange?.(dateWithTime)
  }

  const handleTimeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newTime = e.target.value
    setTime(newTime)
    if (value && isValid(value)) {
      const [hours, minutes] = newTime.split(":").map(Number)
      const dateWithTime = setMinutes(setHours(value, hours || 0), minutes || 0)
      onChange?.(dateWithTime)
    }
  }

  React.useEffect(() => {
    if (value && isValid(value)) {
      setTime(format(value, "HH:mm"))
    }
  }, [value])

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          disabled={disabled}
          className={cn(
            "w-full justify-start text-left font-normal",
            !value && "text-muted-foreground",
            className
          )}
        >
          <CalendarIcon className="mr-2 h-4 w-4" />
          {value && isValid(value) ? (
            format(value, "dd/MM/yyyy HH:mm")
          ) : (
            <span>{placeholder}</span>
          )}
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-auto p-0" align="start">
        <Calendar
          mode="single"
          selected={value}
          onSelect={handleDateSelect}
          initialFocus
        />
        <div className="border-t p-3">
          <Input
            type="time"
            value={time}
            onChange={handleTimeChange}
            className="w-full"
          />
        </div>
      </PopoverContent>
    </Popover>
  )
}
