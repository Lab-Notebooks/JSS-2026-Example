// Empty host stand-in for Pepper's src/event_handle.h. The standalone validator
// calls the kernel's plain *_me2(p, params) helpers directly and never uses the
// event_data template parameter, so no real event handle is needed.
#pragma once
